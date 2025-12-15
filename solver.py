import base64
import json
import requests
import re
import sys
import os
from pathlib import Path

# ===== CONFIGURATION =====
# Default image path matching user's likely workflow
DEFAULT_IMAGE_PATH = "resources/downloads/photo_2025-12-13_09-18-38.jpg"
OCR_API_URL = "https://gaxyqcsvy2ii5nsxz74lgsj3ay0gljec.lambda-url.us-east-1.on.aws/"
DICTIONARY_URL = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
DICTIONARY_FILE = "words_alpha.txt"
# =========================

def image_to_base64_data_url(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    mime = "image/jpeg"
    ext = path.suffix.lower()
    if ext == ".png":
        mime = "image/png"
    elif ext in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    return f"data:{mime};base64,{encoded}"

def get_ocr_result(image_path: str):
    """
    Sends the image to the OCR API and returns the parsed JSON response.
    """
    print(f"[*] Sending image to OCR API: {image_path}")
    
    try:
        data_url = image_to_base64_data_url(image_path)
    except FileNotFoundError:
        print(f"[!] File not found: {image_path}")
        return None

    payload = {"image": data_url}
    headers = {
        "Accept": "*/*",
        "Content-Type": "text/plain;charset=UTF-8",
        "Origin": "https://wordsearchonline.com",
        "Referer": "https://wordsearchonline.com/",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) Chrome/137 Mobile",
    }

    try:
        r = requests.post(
            OCR_API_URL,
            data=json.dumps(payload),
            headers=headers,
            timeout=30
        )
        r.raise_for_status()
        # The API returns a string that might be JSON or plain text
        # If it returns a JSON object, r.json() will work
        # If it returns a string representation of JSON, we interpret that.
        try:
            return r.json()
        except:
             # If response is just text
            return {"text": r.text}
            
    except Exception as e:
        print(f"[!] OCR Request failed: {e}")
        return None

def parse_grid_from_ocr(ocr_text):
    """
    Extracts the character grid from OCR text.
    Assumes the grid appears at the start and consists of lines of uppercase letters.
    """
    lines = ocr_text.split('\n')
    grid = []
    
    # Heuristic: Process lines until we hit a keyword like "words:" or empty gap/different structure
    # We expect an N x N or N x M grid of capitalized letters.
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
            
        # Stop if we encounter the "words:" section
        if "words:" in stripped.lower():
            break
            
        # Clean the line: keep only letters
        # Some OCR might put spaces between letters "A B C" -> "ABC"
        clean_row = re.sub(r'[^a-zA-Z]', '', stripped).upper()
        
        # We only accept rows that have a reasonable length (e.g. > 3) to filter noise
        if len(clean_row) >= 4:
            grid.append(list(clean_row))
    
    return grid

def load_dictionary():
    """
    Loads an English dictionary set for word validation.
    Downloads it if not present.
    """
    words = set()
    path = Path(DICTIONARY_FILE)
    
    # Common slang/game words that might be missing from formal dictionaries
    extra_words = {
        "KINDA", "GONNA", "WANNA", "GOTTA", "GIMME", "LEMME", "CAUSE", 
        "DUNNO", "SORTA", "OUTTA", "INNIT", "YALL", "AINT"
    }
    
    if not path.exists():
        print(f"[*] Dictionary file not found. Downloading from {DICTIONARY_URL}...")
        try:
            r = requests.get(DICTIONARY_URL, timeout=10)
            if r.status_code == 200:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(r.text)
                print("[*] Dictionary downloaded successfully.")
            else:
                print(f"[!] Failed to download dictionary (Status: {r.status_code}). Validation will be skipped.")
                # Even if download fails, return extra_words at least
                return extra_words if extra_words else None
        except Exception as e:
            print(f"[!] Dictionary download error: {e}. Validation will be skipped.")
            return extra_words if extra_words else None
            
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w:
                    words.add(w.upper())
        # Add extras
        words.update(extra_words)
        return words
    except Exception as e:
        print(f"[!] Error reading dictionary: {e}")
        return None

def find_words_in_grid(grid, constraints, dictionary):
    """
    Thinking Algorithm:
    1. Iterate for each constraint (StartChar, Length).
    2. Scan every cell in the grid.
    3. If cell matches StartChar, scan in all 8 directions for a string of Length.
    4. If Candidate string is found, validate against dictionary (if available).
    """
    found_map = {} # Key: Index of constraint, Value: List of words found
    
    rows = len(grid)
    if rows == 0:
        return found_map
    
    # 8 Directions: (row_delta, col_delta)
    directions = [
        (0, 1),  (0, -1),   # Right, Left
        (1, 0),  (-1, 0),   # Down, Up
        (1, 1),  (1, -1),   # Down-Right, Down-Left
        (-1, 1), (-1, -1)   # Up-Right, Up-Left
    ]
    
    for idx, (start_char, length) in enumerate(constraints):
        start_char = start_char.upper()
        candidates = set()
        
        for r in range(rows):
            # Safe column range for this specific row
            cols = len(grid[r])
            for c in range(cols):
                if grid[r][c] == start_char:
                    # Check all directions
                    for dr, dc in directions:
                        # Check if the word fits in this direction
                        end_r = r + (length - 1) * dr
                        end_c = c + (length - 1) * dc
                        
                        # Use loose bounds check first
                        if 0 <= end_r < rows:
                            # Now check if columns are valid for every step
                            # This is important for jagged arrays
                            word_chars = []
                            valid_path = True
                            for k in range(length):
                                curr_r = r + k*dr
                                curr_c = c + k*dc
                                if 0 <= curr_c < len(grid[curr_r]):
                                    word_chars.append(grid[curr_r][curr_c])
                                else:
                                    valid_path = False
                                    break
                            
                            if valid_path:
                                candidate_word = "".join(word_chars)
                                
                                # Validation
                                if dictionary:
                                    if candidate_word in dictionary:
                                        candidates.add(candidate_word)
                                else:
                                    # If no dictionary, return all matches (might be noisy)
                                    candidates.add(candidate_word)
        
        found_map[idx] = list(candidates)
        
    return found_map

def save_grid_to_file(grid, filename="grid.txt"):
    """Saves the current grid to a text file."""
    try:
        with open(filename, "w") as f:
            for row in grid:
                f.write(" ".join(row) + "\n")
        print(f"[*] Grid saved to {filename}")
    except Exception as e:
        print(f"[!] Failed to save grid: {e}")

def load_grid_from_file(filename="grid.txt"):
    """Loads a grid from a text file."""
    try:
        grid = []
        with open(filename, "r") as f:
            for line in f:
                # Remove spaces and newlines to get clean chars
                clean_row = [c.upper() for c in line.strip() if c.isalnum()]
                if clean_row:
                    grid.append(clean_row)
        print(f"[*] Grid loaded from {filename}")
        return grid
    except Exception as e:
        print(f"[!] Failed to load grid: {e}")
        return None

def solve_challenge(image_path, clue_text):
    """
    Programmatic entry point for solving a challenge.
    Returns a dict with 'grid' and 'solutions'.
    """
    # 1. Image -> OCR
    ocr_result = get_ocr_result(image_path)
    if not ocr_result:
        return {"error": "OCR failed"}

    # Extract text
    if isinstance(ocr_result, dict):
        raw_text = ocr_result.get("text", "")
    else:
        raw_text = str(ocr_result)

    # 2. OCR -> Grid
    grid = parse_grid_from_ocr(raw_text)
    if not grid:
        return {"error": "No grid found in image"}

    # 3. Load Dictionary
    dictionary = load_dictionary()
    
    # 4. Parse Clues
    pattern = re.compile(r'([A-Z])\-+\s*\((\d+)\)', re.IGNORECASE)
    constraints = pattern.findall(clue_text)
    
    if not constraints:
        return {
            "grid": grid,
            "solutions": [],
            "error": "No clues found in text"
        }

    # 5. Solve
    parsed_constraints = [(c[0], int(c[1])) for c in constraints]
    solutions_map = find_words_in_grid(grid, parsed_constraints, dictionary)
    
    # Format results
    results = []
    for idx, (char, length) in enumerate(parsed_constraints):
        found_words = solutions_map.get(idx, [])
        results.append({
            "pattern": f"{char.upper()}{'-'*(length-1)} ({length})",
            "found": found_words
        })
        
    return {
        "grid": grid,
        "solutions": results
    }

def main():
    print(f"=== Word Search Solver ===")

    grid = None
    
    # Check if grid.txt exists and ask user
    if Path("grid.txt").exists():
        use_saved = input("[?] Found saved 'grid.txt'. Use it? (Y/n): ").strip().lower()
        if use_saved in ["", "y", "yes"]:
            grid = load_grid_from_file("grid.txt")
    
    # If no grid loaded (or user said no), proceed with Image Processing
    if not grid:
        # 1. Image Path
        image_path = None
        if len(sys.argv) > 1:
            image_path = sys.argv[1]
        
        # Prompt if not provided or doesn't exist
        while not image_path or not Path(image_path).exists():
            if image_path:
                print(f"[!] File not found: {image_path}")
            
            # Suggest the default if it exists, otherwise just blank
            default_hint = f" (default: {DEFAULT_IMAGE_PATH})" if Path(DEFAULT_IMAGE_PATH).exists() else ""
            
            try:
                user_input = input(f"Enter image path{default_hint}: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                sys.exit(0)

            if not user_input and Path(DEFAULT_IMAGE_PATH).exists():
                image_path = DEFAULT_IMAGE_PATH
            elif user_input:
                # Handle quotes in path if user drags and drops file
                image_path = user_input.strip('"\'')
            else:
                print("[!] Please enter a valid path.")
                continue
        
        print(f"[*] Using image: {image_path}")
        
        # 2. Process Image
        ocr_result = get_ocr_result(image_path)
        if not ocr_result:
            print("[!] Failed to get OCR result. Exiting.")
            return

        # Extract text from JSON
        if isinstance(ocr_result, dict):
            raw_text = ocr_result.get("text", "")
        else:
            raw_text = str(ocr_result)
            
        if not raw_text:
            print("[!] OCR returned empty text.")
            return

        # 3. Parse Grid
        grid = parse_grid_from_ocr(raw_text)
        
        if grid:
            save_grid_to_file(grid)
    
    if not grid:
        print("[!] No valid grid detected.")
        return

    print("\n[+] Current Grid:")
    for row in grid:
        print("  " + " ".join(row))
    print(f"    (Size: {len(grid)}x{len(grid[0]) if grid else 0})")

    # 4. Load Dictionary (background task)
    print("\n[*] Loading dictionary for validation...")
    dictionary = load_dictionary()
    if dictionary:
        print(f"[*] Dictionary loaded ({len(dictionary)} words).")
    else:
        print("[!] Warning: Dictionary not available. Results may contain invalid words.")

    # 5. User Input for Challenge
    print("\n" + "="*40)
    print("PASTE THE CHALLENGE TEXT BELOW.")
    print("example: 'Find these words: O--- (4)'")
    print("Press Enter twice to finish input.")
    print("="*40)
    
    user_lines = []
    blank_count = 0
    while True:
        try:
            line = input()
            if not line.strip():
                blank_count += 1
                if blank_count >= 1: # One empty line to stop? Or just keep strict?
                    # Let's say one empty line is enough if we have content
                    if user_lines: break 
            else:
                blank_count = 0
                user_lines.append(line)
        except (EOFError, KeyboardInterrupt):
            break
            
    user_msg = "\n".join(user_lines)
    
    # 6. Parse Constraints
    # Regex for "X--- (N)" format
    # Matches: One letter, hyphens, space, parens with number
    pattern = re.compile(r'([A-Z])\-+\s*\((\d+)\)', re.IGNORECASE)
    constraints = pattern.findall(user_msg)
    
    if not constraints:
        print("[!] No constraints found in message. (Format: 'X--- (4)')")
        return
        
    print(f"\n[*] Found {len(constraints)} patterns to search.")
    
    # 7. Solve
    parsed_constraints = [(c[0], int(c[1])) for c in constraints]
    solutions = find_words_in_grid(grid, parsed_constraints, dictionary)
    
    # 8. Output
    print("\n" + "="*15 + " SOLUTIONS " + "="*15)
    for idx, (char, length) in enumerate(parsed_constraints):
        found = solutions.get(idx, [])
        pattern_str = f"{char.upper()}{'-'*(length-1)} ({length})"
        
        if found:
            print(f"{pattern_str} => {', '.join(found)}")
        else:
            print(f"{pattern_str} => [Not Found]")
    print("="*41)

if __name__ == "__main__":
    main()
