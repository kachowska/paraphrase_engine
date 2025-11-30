"""
Block 4: Document Builder
Automatically replaces original fragments with paraphrased ones in .docx documents
"""

import os
import logging
from typing import List, Tuple, Optional
from pathlib import Path
import shutil
from docx import Document
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from ..block5_logging.logger import SystemLogger

logger = logging.getLogger(__name__)


class DocumentBuilder:
    """Handles document manipulation and fragment replacement"""
    
    def __init__(self):
        self.system_logger = SystemLogger()
    
    async def replace_fragments(
        self,
        source_file_path: str,
        output_file_path: str,
        original_fragments: List[str],
        paraphrased_fragments: List[str]
    ) -> bool:
        """
        Replace fragments in document
        CRITICAL: Replacements are made in reverse order to preserve text indexing
        
        Args:
            source_file_path: Path to source .docx file
            output_file_path: Path for output .docx file
            original_fragments: List of original text fragments
            paraphrased_fragments: List of paraphrased text fragments
            
        Returns:
            bool: True if successful, False otherwise
        """
        
        if len(original_fragments) != len(paraphrased_fragments):
            logger.error("Mismatch between original and paraphrased fragments count")
            return False
        
        try:
            # Create a copy of the source file
            shutil.copy2(source_file_path, output_file_path)
            logger.info(f"Created document copy: {output_file_path}")
            
            # Open the document
            doc = Document(output_file_path)
            
            # Process replacements in REVERSE order (critical requirement)
            replacements_made = 0
            skipped_fragments = []
            
            for i in range(len(original_fragments) - 1, -1, -1):
                original = original_fragments[i]
                paraphrased = paraphrased_fragments[i]
                
                logger.info(f"Processing fragment {i + 1}/{len(original_fragments)} (reverse order)")
                
                # Try to replace the fragment
                replaced = await self._replace_fragment_in_document(
                    doc,
                    original,
                    paraphrased,
                    fragment_index=i
                )
                
                if replaced:
                    replacements_made += 1
                    await self.system_logger.log_fragment_replaced(
                        fragment_index=i,
                        original_length=len(original),
                        paraphrased_length=len(paraphrased)
                    )
                else:
                    skipped_fragments.append(i)
                    await self.system_logger.log_fragment_not_found(
                        fragment_index=i,
                        fragment_text=original[:50] + "..." if len(original) > 50 else original
                    )
            
            # Save the modified document
            doc.save(output_file_path)
            
            logger.info(
                f"Document processing complete. "
                f"Replacements: {replacements_made}/{len(original_fragments)}, "
                f"Skipped: {len(skipped_fragments)}"
            )
            
            # Log completion
            await self.system_logger.log_document_processed(
                source_path=source_file_path,
                output_path=output_file_path,
                total_fragments=len(original_fragments),
                replaced_fragments=replacements_made,
                skipped_fragments=len(skipped_fragments)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            await self.system_logger.log_error(
                chat_id=0,
                operation="document_builder",
                error_message=str(e)
            )
            return False
    
    async def _replace_fragment_in_document(
        self,
        doc: Document,
        original_text: str,
        replacement_text: str,
        fragment_index: int
    ) -> bool:
        """
        Replace a single fragment in the document
        
        Returns:
            bool: True if replacement was made, False if fragment not found
        """
        
        # Normalize texts for comparison (soft normalization)
        original_normalized = self._normalize_text(original_text)
        
        # Track if replacement was made
        replacement_made = False
        
        # Search through all paragraphs
        for paragraph in doc.paragraphs:
            paragraph_text = paragraph.text
            paragraph_normalized = self._normalize_text(paragraph_text)
            
            # Check if the fragment exists in this paragraph (exact match preferred)
            # First try exact match
            if original_text in paragraph_text:
                success = self._replace_in_paragraph_with_formatting(
                    paragraph,
                    original_text,
                    replacement_text
                )
                
                if success:
                    replacement_made = True
                    logger.info(f"Replaced fragment {fragment_index} in paragraph (exact match)")
                    break
            
            # If exact match failed, try normalized match
            elif original_normalized in paragraph_normalized:
                # Try to find the actual text in the paragraph (accounting for whitespace differences)
                actual_text = self._find_actual_text_in_paragraph(paragraph, original_normalized)
                
                if actual_text:
                    success = self._replace_in_paragraph_with_formatting(
                        paragraph,
                        actual_text,
                        replacement_text
                    )
                    
                    if success:
                        replacement_made = True
                        logger.info(f"Replaced fragment {fragment_index} in paragraph (normalized match)")
                        break
        
        # Also check in tables
        if not replacement_made:
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            paragraph_text = paragraph.text
                            paragraph_normalized = self._normalize_text(paragraph_text)
                            
                            # Try exact match first
                            if original_text in paragraph_text:
                                success = self._replace_in_paragraph_with_formatting(
                                    paragraph,
                                    original_text,
                                    replacement_text
                                )
                                
                                if success:
                                    replacement_made = True
                                    logger.info(f"Replaced fragment {fragment_index} in table (exact match)")
                                    break
                            
                            # Try normalized match
                            elif original_normalized in paragraph_normalized:
                                actual_text = self._find_actual_text_in_paragraph(paragraph, original_normalized)
                                
                                if actual_text:
                                    success = self._replace_in_paragraph_with_formatting(
                                        paragraph,
                                        actual_text,
                                        replacement_text
                                    )
                                    
                                    if success:
                                        replacement_made = True
                                        logger.info(f"Replaced fragment {fragment_index} in table (normalized match)")
                                        break
                        
                        if replacement_made:
                            break
                    
                    if replacement_made:
                        break
                
                if replacement_made:
                    break
        
        if not replacement_made:
            logger.warning(
                f"Fragment {fragment_index} not found in document. "
                f"Original: {original_text[:100]}..."
            )
        
        return replacement_made
    
    def _replace_in_paragraph_with_formatting(
        self,
        paragraph: Paragraph,
        original_text: str,
        replacement_text: str
    ) -> bool:
        """
        Replace text in paragraph while preserving formatting
        
        This is a complex operation that tries to maintain the original formatting
        Handles cases where text spans multiple runs
        """
        
        try:
            # Get full paragraph text
            full_text = paragraph.text
            
            # Check if original text exists (try exact match first)
            start_index = full_text.find(original_text)
            
            if start_index == -1:
                # Try normalized match
                normalized_full = self._normalize_text(full_text)
                normalized_original = self._normalize_text(original_text)
                
                if normalized_original not in normalized_full:
                    return False
                
                # Find normalized positions
                norm_start = normalized_full.find(normalized_original)
                norm_end = norm_start + len(normalized_original)
                
                # Build mapping from normalized positions to actual positions
                # by simulating the normalization process
                norm_to_actual = {}  # Maps normalized index to actual index
                norm_pos = 0
                in_whitespace = False
                
                for actual_pos, char in enumerate(full_text):
                    if not char.isspace():
                        # Non-whitespace character: always contributes to normalized text
                        norm_to_actual[norm_pos] = actual_pos
                        norm_pos += 1
                        in_whitespace = False
                    else:
                        # Whitespace: only first whitespace in sequence contributes
                        if not in_whitespace:
                            norm_to_actual[norm_pos] = actual_pos
                            norm_pos += 1
                            in_whitespace = True
                        # Subsequent whitespace doesn't contribute to normalized text
                
                # Map normalized start and end to actual positions
                if norm_start in norm_to_actual:
                    start_index = norm_to_actual[norm_start]
                else:
                    return False
                
                # For end position, find the actual position corresponding to norm_end
                # If exact match not found, use the position after the last character
                # that contributes to normalized text up to norm_end
                if norm_end in norm_to_actual:
                    end_index = norm_to_actual[norm_end]
                else:
                    # Find the last actual position that maps to a normalized position < norm_end
                    # and set end_index to the position after it
                    max_actual = -1
                    for norm_idx, actual_idx in norm_to_actual.items():
                        if norm_idx < norm_end:
                            max_actual = max(max_actual, actual_idx)
                    if max_actual >= 0:
                        # Find the end of the whitespace sequence or next non-whitespace
                        end_index = max_actual + 1
                        # Skip any trailing whitespace after this position
                        while end_index < len(full_text) and full_text[end_index].isspace():
                            end_index += 1
                    else:
                        end_index = len(full_text)
            else:
                end_index = start_index + len(original_text)
            
            # Build new paragraph content
            new_runs = []
            current_pos = 0
            replacement_added = False
            
            for run in paragraph.runs:
                run_text = run.text
                run_start = current_pos
                run_end = current_pos + len(run_text)
                
                # Case 1: Run is completely before the replacement area
                if run_end <= start_index:
                    new_runs.append((run_text, run))
                
                # Case 2: Run is completely after the replacement area
                elif run_start >= end_index:
                    new_runs.append((run_text, run))
                
                # Case 3: Run contains the start of replacement area
                elif run_start < start_index and run_end > start_index:
                    # Part before replacement
                    before_text = run_text[:start_index - run_start]
                    if before_text:
                        new_runs.append((before_text, run))
                    
                    # Add replacement text with same formatting (only once)
                    if not replacement_added:
                        new_runs.append((replacement_text, run))
                        replacement_added = True
                    
                    # Check if replacement ends in this run
                    if run_end >= end_index:
                        # Part after replacement
                        after_text = run_text[end_index - run_start:]
                        if after_text:
                            new_runs.append((after_text, run))
                
                # Case 4: Run is completely within replacement area
                elif run_start >= start_index and run_end <= end_index:
                    # Skip this run (it's being replaced)
                    # But add replacement if we haven't yet
                    if not replacement_added:
                        new_runs.append((replacement_text, run))
                        replacement_added = True
                
                # Case 5: Run contains the end of replacement area
                elif run_start < end_index and run_end > end_index:
                    # Add replacement if we haven't yet
                    if not replacement_added:
                        new_runs.append((replacement_text, run))
                        replacement_added = True
                    
                    # Part after replacement
                    after_text = run_text[end_index - run_start:]
                    if after_text:
                        new_runs.append((after_text, run))
                
                current_pos = run_end
            
            # If replacement wasn't added (edge case), add it at the start position
            if not replacement_added:
                # Find the run that contains start_index
                current_pos = 0
                for i, run in enumerate(paragraph.runs):
                    run_start = current_pos
                    run_end = current_pos + len(run.text)
                    if run_start <= start_index < run_end:
                        # Insert replacement before this run
                        new_runs.insert(i, (replacement_text, run))
                        break
                    current_pos = run_end
            
            # Clear paragraph and rebuild with new runs
            paragraph.clear()
            
            for text, original_run in new_runs:
                if text:  # Only add non-empty runs
                    new_run = paragraph.add_run(text)
                    # Copy formatting from original run
                    self._copy_run_formatting(original_run, new_run)
            
            return True
            
        except Exception as e:
            logger.error(f"Error replacing text with formatting: {e}", exc_info=True)
            
            # Fallback: Simple replacement without formatting preservation
            try:
                full_text = paragraph.text
                paragraph.text = full_text.replace(original_text, replacement_text)
                logger.warning(f"Used fallback replacement method for paragraph")
                return True
            except Exception as fallback_error:
                logger.error(f"Fallback replacement also failed: {fallback_error}")
                return False
    
    def _copy_run_formatting(self, source_run: Run, target_run: Run):
        """Copy formatting from source run to target run"""
        try:
            if source_run.bold is not None:
                target_run.bold = source_run.bold
            if source_run.italic is not None:
                target_run.italic = source_run.italic
            if source_run.underline is not None:
                target_run.underline = source_run.underline
            if source_run.font.name:
                target_run.font.name = source_run.font.name
            if source_run.font.size:
                target_run.font.size = source_run.font.size
            if source_run.font.color.rgb:
                target_run.font.color.rgb = source_run.font.color.rgb
            if source_run.font.highlight_color:
                target_run.font.highlight_color = source_run.font.highlight_color
        except Exception as e:
            logger.debug(f"Could not copy some formatting: {e}")
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison
        Handles different whitespace, line breaks, etc.
        Uses soft normalization to preserve text structure
        """
        import re
        # Normalize line endings first
        text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
        # Replace multiple spaces/tabs with single space (but preserve single spaces)
        text = re.sub(r'[ \t]+', ' ', text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text
    
    def _find_actual_text_in_paragraph(self, paragraph: Paragraph, normalized_search: str) -> Optional[str]:
        """
        Find the actual text in paragraph that matches normalized search string
        Accounts for whitespace differences while preserving the actual text structure
        """
        # Get all text from runs
        full_text = paragraph.text
        normalized_full = self._normalize_text(full_text)
        
        # Find position in normalized text
        start_pos = normalized_full.find(normalized_search)
        if start_pos == -1:
            return None
        
        # Try to find corresponding position in actual text
        # This is approximate - we'll use a sliding window approach
        search_length = len(normalized_search)
        
        # Build normalized text with position mapping
        normalized_chars = []
        actual_chars = []
        pos = 0
        
        for run in paragraph.runs:
            for char in run.text:
                actual_chars.append((char, pos))
                normalized_char = self._normalize_text(char)
                if normalized_char:
                    normalized_chars.append((normalized_char, pos))
                pos += 1
        
        # Find start and end positions
        normalized_text = ''.join([c[0] for c in normalized_chars])
        search_start = normalized_text.find(normalized_search)
        
        if search_start == -1:
            return None
        
        # Map back to actual text positions
        # This is complex, so we'll use a simpler approach:
        # Extract a window from the actual text that should contain our fragment
        actual_start = 0
        actual_end = len(full_text)
        
        # Count normalized characters to find approximate position
        norm_count = 0
        for i, char in enumerate(full_text):
            norm_char = self._normalize_text(char)
            if norm_char:
                if norm_count == search_start:
                    actual_start = i
                if norm_count == search_start + search_length:
                    actual_end = i
                    break
                norm_count += 1
        
        # Extract candidate text
        candidate = full_text[actual_start:actual_end]
        
        # Verify it normalizes to our search string
        if self._normalize_text(candidate) == normalized_search:
            return candidate
        
        # If exact match failed, try to find by searching for key words
        # Split normalized search into words
        search_words = normalized_search.split()
        if len(search_words) < 2:
            return None
        
        # Find first and last words in actual text
        first_word = search_words[0]
        last_word = search_words[-1]
        
        first_pos = full_text.find(first_word)
        if first_pos == -1:
            return None
        
        # Find last word after first word
        last_pos = full_text.find(last_word, first_pos)
        if last_pos == -1:
            return None
        
        # Extract text between first and last word (with some padding)
        candidate = full_text[first_pos:last_pos + len(last_word)]
        
        # Verify normalization
        if self._normalize_text(candidate) == normalized_search:
            return candidate
        
        return None
    
    async def validate_document(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a file is a valid .docx document
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not os.path.exists(file_path):
                return False, "File does not exist"
            
            if not file_path.endswith('.docx'):
                return False, "File is not a .docx document"
            
            # Try to open the document
            doc = Document(file_path)
            
            # Check if document has content
            has_content = False
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    has_content = True
                    break
            
            if not has_content:
                # Check tables
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            if cell.text.strip():
                                has_content = True
                                break
                        if has_content:
                            break
                    if has_content:
                        break
            
            if not has_content:
                return False, "Document appears to be empty"
            
            return True, None
            
        except Exception as e:
            return False, f"Error reading document: {str(e)}"
    
    async def extract_text(self, file_path: str) -> List[str]:
        """
        Extract all text from a document as a list of paragraphs
        Useful for debugging and validation
        """
        try:
            doc = Document(file_path)
            paragraphs = []
            
            # Extract from paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    paragraphs.append(paragraph.text)
            
            # Extract from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if paragraph.text.strip():
                                paragraphs.append(paragraph.text)
            
            return paragraphs
            
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return []