import os
import re
import datetime
import yaml

def process_inline_formatting(text):
    text = text.replace('\\', '\\\\')
    text = re.sub(r'\*\*(.*?)\*\*|__(.*?)__', lambda m: f'\\fB{m.group(1) or m.group(2)}\\fR', text)
    text = re.sub(r'\*(.*?)\*|_(.*?)_', lambda m: f'\\fI{m.group(1) or m.group(2)}\\fR', text)
    text = re.sub(r'`(.*?)`', r'\\fB\1\\fR', text)
    return text

def convert_md_to_man(md_content, default_name="manual"):
    lines = md_content.splitlines()
    
    frontmatter = {}
    if md_content.startswith('---'):
        fm_lines = []
        idx = 1
        while idx < len(lines) and lines[idx] != '---':
            fm_lines.append(lines[idx])
            idx += 1
        if idx < len(lines):
            lines = lines[idx+1:]
            fm_text = '\n'.join(fm_lines)
            try:
                frontmatter = yaml.safe_load(fm_text) or {}
            except Exception:
                pass

    title = default_name.upper()
    section = "1"
    date_str = datetime.date.today().strftime("%B %Y")
    version = "1.0"
    manual = "User Commands"
    description = ""

    first_heading_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('# '):
            first_heading_idx = i
            match = re.match(r'^#\s+([a-zA-Z0-9_\-]+)\s*(?:\((\d+)\))?\s*(?:\-\s*(.*))?$', line)
            if match:
                title = match.group(1).upper()
                if match.group(2):
                    section = match.group(2)
                if match.group(3):
                    description = match.group(3)
            break

    if 'title' in frontmatter:
        title = str(frontmatter['title']).upper()
    if 'section' in frontmatter:
        section = str(frontmatter['section'])
    if 'date' in frontmatter:
        date_str = str(frontmatter['date'])
    if 'version' in frontmatter:
        version = str(frontmatter['version'])
    if 'manual' in frontmatter:
        manual = str(frontmatter['manual'])
    if 'description' in frontmatter:
        description = str(frontmatter['description'])

    man_lines = []
    man_lines.append(f'.TH {title} {section} "{date_str}" "{version}" "{manual}"')
    
    if description:
        man_lines.append('.SH NAME')
        man_lines.append(f'{title.lower()} \\- {description}')

    in_code_block = False
    in_list = False

    start_idx = first_heading_idx + 1 if first_heading_idx != -1 else 0
    for line in lines[start_idx:]:
        line_stripped = line.strip()
        
        if line_stripped.startswith('```'):
            if in_code_block:
                man_lines.append('.fi')
                in_code_block = False
            else:
                man_lines.append('.nf')
                in_code_block = True
            continue

        if in_code_block:
            man_lines.append(line)
            continue

        if line.startswith('## '):
            man_lines.append('.SH ' + line[3:].strip().upper())
            continue
        elif line.startswith('### '):
            man_lines.append('.SS ' + line[4:].strip())
            continue
        elif line.startswith('# '):
            man_lines.append('.SH ' + line[2:].strip().upper())
            continue

        list_match = re.match(r'^(\-|\*)\s+(.*)$', line_stripped)
        ordered_list_match = re.match(r'^(\d+)\.\s+(.*)$', line_stripped)
        
        if list_match:
            man_lines.append('.IP \\(bu 2')
            content = list_match.group(2)
            man_lines.append(process_inline_formatting(content))
            in_list = True
            continue
        elif ordered_list_match:
            num = ordered_list_match.group(1)
            man_lines.append(f'.IP {num}. 2')
            content = ordered_list_match.group(2)
            man_lines.append(process_inline_formatting(content))
            in_list = True
            continue

        if line_stripped == "":
            if not in_list:
                man_lines.append('.PP')
            in_list = False
            continue

        man_lines.append(process_inline_formatting(line_stripped))

    return '\n'.join(man_lines), title.lower(), section

def generate_man_pages(docs_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    man_count = 0
    for root, dirs, files in os.walk(docs_dir):
        for file in files:
            if not file.endswith('.md'):
                continue
            file_path = os.path.join(root, file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue
            
            is_man = 'man/' in file_path or 'man: true' in content or 'man_section:' in content
            if not is_man:
                continue
            
            default_name = os.path.splitext(file)[0]
            try:
                man_content, name, section = convert_md_to_man(content, default_name)
                
                sec_dir = os.path.join(output_dir, f"man{section}")
                os.makedirs(sec_dir, exist_ok=True)
                
                out_path = os.path.join(sec_dir, f"{name}.{section}")
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(man_content)
                man_count += 1
            except Exception as e:
                print(f"Failed to generate man page for {file_path}: {e}")
    return man_count
