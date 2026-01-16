#!/usr/bin/env python3
"""
Documentation Generator for UE Height Maps
Generates README.md file for the workspace structure.
"""

import os
import json
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import quote, urlencode


class DocGenerator:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.structure = defaultdict(lambda: defaultdict(list))
        
    def scan_directory(self):
        """Scan the directory structure and organize data."""
        for game_dir in self.root_path.iterdir():
            if not game_dir.is_dir():
                continue
            
            if game_dir.name.startswith('.'):
                continue

            game_name = game_dir.name
            
            for version_dir in game_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                    
                version = version_dir.name
                terrains = []
                
                # Scan terrain folders
                for terrain_dir in version_dir.iterdir():
                    if not terrain_dir.is_dir():
                        continue
                        
                    terrain_name = terrain_dir.name
                    maps = []
                    
                    # Check for sub-maps (like Lobby, Main Island)
                    has_submaps = False
                    for item in terrain_dir.iterdir():
                        if item.is_dir() and not item.name.startswith('Guid_'):
                            has_submaps = True
                            submap_name = item.name
                            guid_folders = [f.name for f in item.iterdir() if f.is_dir()]
                            maps.append({
                                'name': submap_name,
                                'guids': guid_folders
                            })
                    
                    # If no submaps, check for direct GUID folders
                    if not has_submaps:
                        guid_files = [f.name for f in terrain_dir.iterdir() if f.name.startswith('Guid_')]
                        if guid_files:
                            maps.append({
                                'name': terrain_name,
                                'guids': guid_files
                            })
                    
                    if maps:
                        terrains.append({
                            'name': terrain_name,
                            'maps': maps
                        })
                
                if terrains:
                    self.structure[game_name][version] = terrains
    
    def generate_readme(self):
        """Generate README.md for the root directory."""
        # Compute hash of all games structure
        all_structure = json.dumps(self.structure, sort_keys=True, default=list)
        root_hash = hashlib.md5(all_structure.encode()).hexdigest()
        
        lines = []
        lines.append(f"<!-- hash:{root_hash} -->")
        lines.append("# Unreal Engine Height Maps Collection\n")
        lines.append(f"*Generated on {datetime.now().astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}*\n")
        lines.append("This repository contains extracted height map and weight maps data from various Unreal Engine games.\n")
        
        lines.append("## Extractor\n")
        lines.append("The height maps were extracted using the following tool:\n")
        lines.append(f"Extractor Tool: [UE Height Map Extractor](https://github.com/MinshuG/UEHeightMapExtracter)\n")

        lines.append("## Overview\n")
        lines.append("The repository contains terrain height maps organized by game and version.\n")
        
        lines.append("## Games\n")
        for game in sorted(self.structure.keys()):
            version_count = len(self.structure[game])
            lines.append(f"### {game}\n")
            lines.append(f"- **Versions**: {version_count}\n")

            string = ""
            for version in sorted(self.structure[game].keys(), key=self._version_sort_key):
                relative_url = quote(f"{game}/{version}")
                string += f"[{version}]({relative_url}), "
            string = string.rstrip(", ")

            lines.append(f"- **Available versions**: {string}\n")
        
        lines.append("## Structure\n")
        lines.append("```")
        lines.append("Game/")
        lines.append("  └── Version/")
        lines.append("      └── Terrain_Name/")
        lines.append("          └── Map_Name/")
        lines.append("```\n")
        
        return '\n'.join(lines)
    
    def generate_game_readme(self, game_name):
        """Generate README.md for a specific game directory."""
        if game_name not in self.structure:
            return None
        
        # Compute hash for this game
        game_hash = self._compute_game_hash(game_name)

        lines = []
        lines.append(f"<!-- hash:{game_hash} -->")
        lines.append(f"# {game_name} Height Maps\n")
        lines.append(f"*Generated on {datetime.now().astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}*\n")

        lines.append("## Versions\n")
        lines.append("| Version | Terrains | Maps |")
        lines.append("|---------|----------|------|")

        for version in sorted(self.structure[game_name].keys(), key=self._version_sort_key):
            terrains = self.structure[game_name][version]
            terrain_names = [t['name'] for t in terrains]
            total_maps = sum(len(t['maps']) for t in terrains)
            lines.append(f"| [{version}]({quote(version)}) | {', '.join(terrain_names)} | {total_maps} |")

        return '\n'.join(lines)
    
    def _version_sort_key(self, version):
        """Sort key for version numbers."""
        try:
            parts = version.replace('Pre Alpha', '0.0').split('.')
            return tuple(int(p) if p.isdigit() else 0 for p in parts)
        except:
            return (0,)
    
    def _compute_game_hash(self, game_name):
        """Compute a hash of a specific game's structure."""
        if game_name not in self.structure:
            return None
        # Create a stable string representation of the game structure
        game_structure = dict(self.structure[game_name])
        structure_str = json.dumps(game_structure, sort_keys=True, default=list)
        return hashlib.md5(structure_str.encode()).hexdigest()
    
    def _extract_hash_from_readme(self, readme_path):
        """Extract the structure hash from an existing README file."""
        if not readme_path.exists():
            return None
        
        try:
            content = readme_path.read_text(encoding='utf-8')
            # Look for hash in HTML comment: <!-- hash:XXXXX -->
            import re
            match = re.search(r'<!-- hash:([a-f0-9]+) -->', content)
            if match:
                return match.group(1)
        except:
            pass
        return None
    
    def _game_has_changes(self, game_name):
        """Check if a specific game's structure has changed."""
        current_hash = self._compute_game_hash(game_name)
        readme_path = self.root_path / game_name / 'README.md'
        stored_hash = self._extract_hash_from_readme(readme_path)
        
        return current_hash != stored_hash
    
    def save_files(self, force=False):
        """Save generated documentation files."""
        files_generated = False
        
        # Check root README
        root_readme_path = self.root_path / 'README.md'
        root_hash = self._extract_hash_from_readme(root_readme_path)
        all_structure = json.dumps(self.structure, sort_keys=True, default=list)
        current_root_hash = hashlib.md5(all_structure.encode()).hexdigest()
        
        if force or root_hash != current_root_hash:
            readme_content = self.generate_readme()
            root_readme_path.write_text(readme_content, encoding='utf-8')
            print(f"✓ Generated {root_readme_path}")
            files_generated = True
        else:
            print(f"→ Skipped {root_readme_path} (no changes)")

        # Generate README for each game (only if changed)
        for game_name in sorted(self.structure.keys()):
            if force or self._game_has_changes(game_name):
                game_readme = self.generate_game_readme(game_name)
                if game_readme:
                    game_readme_path = self.root_path / game_name / 'README.md'
                    game_readme_path.write_text(game_readme, encoding='utf-8')
                    print(f"✓ Generated {game_readme_path}")
                    files_generated = True
            else:
                print(f"→ Skipped {game_name}/README.md (no changes)")
        
        return files_generated


def main():
    """Main entry point."""
    import sys
    
    # Get the script's directory or use current directory
    script_dir = Path(__file__).parent
    
    # Check for --force flag
    force = '--force' in sys.argv
    
    print("UE Height Maps Docs Generator")
    print("=" * 50)
    print(f"Scanning: {script_dir}")
    print()
    
    generator = DocGenerator(script_dir)
    generator.scan_directory()
    
    if generator.save_files(force=force):
        print()
        print("Documentation generation complete!")
    else:
        print()
        print("No documentation generated.")


if __name__ == '__main__':
    main()
