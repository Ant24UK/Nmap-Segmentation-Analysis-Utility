import glob
import os
import re

# ANSI colour codes for terminal output
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def strip_ansi(s):
    return re.sub(r'\x1b\[[0-9;]*m', '', s)

def pad_cell(s, width):
    real_len = len(strip_ansi(s))
    return s + ' ' * (width - real_len)

# Helper to get segment type and name from filename
def parse_segment(filename):
    base = os.path.splitext(filename)[0]
    if base.lower().startswith("pci -"):
        return "pci", base[6:].strip()
    elif base.lower().startswith("non pci -"):
        return "non_pci", base[10:].strip()
    else:
        return "unknown", base

# Find all .gnmap files in the current directory
gnmap_files = glob.glob("*.gnmap")

segment_hosts = {}
segment_types = {}

for gnmap_file in gnmap_files:
    seg_type, seg_name = parse_segment(gnmap_file)
    segment_types[seg_name] = seg_type
    hosts = set()
    with open(gnmap_file, "r") as f:
        for line in f:
            if line.startswith("Host:"):
                parts = line.split()
                ip = parts[1]
                if "Ports:" in line and "open" in line:
                    hosts.add(ip)
    segment_hosts[seg_name] = hosts

# Collect all unique hosts
all_hosts = set()
for hosts in segment_hosts.values():
    all_hosts.update(hosts)
all_hosts = sorted(all_hosts)

# Sort segments: PCI first, then NON PCI, then unknown
pci_segments = [seg for seg, typ in segment_types.items() if typ == "pci"]
non_pci_segments = [seg for seg, typ in segment_types.items() if typ == "non_pci"]
unknown_segments = [seg for seg, typ in segment_types.items() if typ not in ("pci", "non_pci")]
ordered_segments = pci_segments + non_pci_segments + unknown_segments

# Set column widths for terminal output
host_col_width = max(15, max(len(h) for h in all_hosts) + 2)
seg_col_width = max(15, max(len(seg) for seg in segment_hosts.keys()) + 2)

# Print PCI/NON PCI Segment Table
print(f"{BOLD}Segment Classification:{RESET}")
print(f"{GREEN}PCI Segments:{RESET} {', '.join(pci_segments) if pci_segments else 'None'}")
print(f"{YELLOW}NON PCI Segments:{RESET} {', '.join(non_pci_segments) if non_pci_segments else 'None'}")
print("-" * (host_col_width + seg_col_width * len(segment_hosts)))

# Print a key/legend
print(f"{BOLD}Key:{RESET}")
print(f"{GREEN}X{RESET} = Host is reachable from this segment (at least one open port found)")
print(f"{YELLOW}X{RESET} = Host is reachable from multiple segments (potential segmentation issue)")
print(f"{RED}X{RESET} = Host is reachable from both PCI and non-PCI segments (critical concern)")
print("-" * (host_col_width + seg_col_width * len(segment_hosts)))

# Print a communication matrix with segments as columns (PCI first)
print(f"{BOLD}Communication Matrix:{RESET} (see key above)\n")
header = pad_cell("Host", host_col_width) + " " + " ".join([pad_cell(seg, seg_col_width) for seg in ordered_segments])
print(header)
print("-" * len(header))
for h in all_hosts:
    row = pad_cell(h, host_col_width) + " "
    segments_reaching = [seg for seg in segment_hosts if h in segment_hosts[seg]]
    has_pci = any(segment_types.get(seg, "") == "pci" for seg in segments_reaching)
    has_non_pci = any(segment_types.get(seg, "") == "non_pci" for seg in segments_reaching)
    for segment in ordered_segments:
        if h in segment_hosts[segment]:
            if has_pci and has_non_pci:
                cell = f"{RED}X{RESET}"
            elif len(segments_reaching) > 1:
                cell = f"{YELLOW}X{RESET}"
            else:
                cell = f"{GREEN}X{RESET}"
        else:
            cell = "-"
        row += pad_cell(cell, seg_col_width)
    print(row)

# Highlight areas of concern
print(f"\n{BOLD}Areas of Concern:{RESET}")
concern_found = False
areas_of_concern = []
for h in all_hosts:
    segments_reaching = [seg for seg in segment_hosts if h in segment_hosts[seg]]
    has_pci = any(segment_types.get(seg, "") == "pci" for seg in segments_reaching)
    has_non_pci = any(segment_types.get(seg, "") == "non_pci" for seg in segments_reaching)
    multi = len(segments_reaching) > 1
    pci_and_nonpci = has_pci and has_non_pci
    if multi or pci_and_nonpci:
        concern_found = True
        if multi:
            msg = f"- Host {h} is reachable from multiple segments: {', '.join(segments_reaching)}"
            print(f"{YELLOW}{msg}{RESET}")
            areas_of_concern.append(('yellow', msg))
        if pci_and_nonpci:
            msg = f"[!] Host {h} is reachable from both PCI and non-PCI segments: {', '.join(segments_reaching)}"
            print(f"{RED}{msg}{RESET}")
            areas_of_concern.append(('red', msg))
if not concern_found:
    print("No areas of concern detected based on current matrix.")

# Client-friendly breakdown
print(f"\n{BOLD}Client Breakdown:{RESET}")
print("This matrix shows which network segments can communicate with which hosts. Each 'X' means that the host was reachable from that segment during testing.")
print(f"{YELLOW}Yellow X{RESET}: Indicates a host is reachable from more than one segment, which may suggest insufficient network segmentation.")
print(f"{RED}Red X{RESET}: Indicates a host is reachable from both PCI and non-PCI segments, which is a critical concern for compliance and security.")
print("We recommend reviewing any yellow or red entries to ensure your segmentation controls meet your policy and compliance requirements.")

# --- HTML Output ---
with open("segmentation_matrix.html", "w") as f:
    f.write("<html><body>\n")
    f.write("<h2>Segment Classification</h2>\n")
    f.write("<ul>")
    f.write(f"<li><b style='color:green;'>PCI Segments:</b> {', '.join(pci_segments) if pci_segments else 'None'}</li>")
    f.write(f"<li><b style='color:orange;'>NON PCI Segments:</b> {', '.join(non_pci_segments) if non_pci_segments else 'None'}</li>")
    f.write("</ul>")

    f.write("<h2>Communication Matrix</h2>\n")
    f.write("<table border='1' cellpadding='5' style='border-collapse:collapse;'>\n")
    # Header
    f.write("<tr><th>Host</th>")
    for seg in ordered_segments:
        if seg in pci_segments:
            f.write(f"<th style='background:#b3d1ff;color:#003366;'>{seg}</th>")  # Blue for PCI
        elif seg in non_pci_segments:
            f.write(f"<th style='background:#fff2cc;color:#7f6000;'>{seg}</th>")  # Light yellow for NON PCI
        else:
            f.write(f"<th>{seg}</th>")
    f.write("</tr>\n")
    # Rows
    for h in all_hosts:
        f.write(f"<tr><td>{h}</td>")
        segments_reaching = [seg for seg in segment_hosts if h in segment_hosts[seg]]
        has_pci = any(segment_types.get(seg, "") == "pci" for seg in segments_reaching)
        has_non_pci = any(segment_types.get(seg, "") == "non_pci" for seg in segments_reaching)
        for segment in ordered_segments:
            if h in segment_hosts[segment]:
                if has_pci and has_non_pci:
                    colour = "#ffcccc"  # Red
                elif len(segments_reaching) > 1:
                    colour = "#ffff99"  # Yellow
                else:
                    colour = "#ccffcc"  # Green
                f.write(f"<td style='background:{colour};text-align:center;'>X</td>")
            else:
                f.write("<td style='text-align:center;'>-</td>")
        f.write("</tr>\n")
    f.write("</table>\n")
    f.write("<p><b>Key:</b><br>")
    f.write("<span style='background:#ccffcc;'>Green</span>: Host is reachable from this segment only.<br>")
    f.write("<span style='background:#ffff99;'>Yellow</span>: Host is reachable from multiple segments.<br>")
    f.write("<span style='background:#ffcccc;'>Red</span>: Host is reachable from both PCI and non-PCI segments.<br>")
    f.write("</p>\n")
    # Areas of Concern in HTML
    f.write("<h2>Areas of Concern</h2>\n")
    if areas_of_concern:
        for colour, msg in areas_of_concern:
            if colour == 'red':
                f.write(f"<div style='color:#b20000;font-weight:bold;'>{msg}</div>\n")
            elif colour == 'yellow':
                f.write(f"<div style='color:#b59b00;'>{msg}</div>\n")
    else:
        f.write("<div>No areas of concern detected based on current matrix.</div>\n")
    f.write("</body></html>\n")

print(f"\n{CYAN}HTML report generated: segmentation_matrix.html{RESET}")
