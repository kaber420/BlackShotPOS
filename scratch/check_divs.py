import sys

def check_divs(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    open_divs = []
    
    for i, line in enumerate(lines):
        line_num = i + 1
        # Count <div and </div
        # This is a very rough check, doesn't handle strings/comments perfectly but good for broad overview
        pos = 0
        while True:
            start_idx = line.find('<div', pos)
            end_idx = line.find('</div>', pos)
            
            if start_idx == -1 and end_idx == -1:
                break
                
            if start_idx != -1 and (end_idx == -1 or start_idx < end_idx):
                open_divs.append(line_num)
                pos = start_idx + 4
            else:
                if open_divs:
                    open_divs.pop()
                else:
                    print(f"Error: Unexpected </div> at line {line_num}")
                pos = end_idx + 6
                
    if open_divs:
        print(f"Error: Unclosed <div> tags started at lines: {open_divs}")
    else:
        print("Divs are balanced!")

if __name__ == "__main__":
    check_divs(sys.argv[1])
