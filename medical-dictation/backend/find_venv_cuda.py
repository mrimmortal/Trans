# find_venv_cuda.py
import sys
import os
import glob

print("=" * 60)
print("Virtual Environment Info")
print("=" * 60)
print(f"Python executable: {sys.executable}")
print(f"Virtual env: {sys.prefix}")
print()

# Find site-packages in virtual environment
for path in sys.path:
    if 'site-packages' in path:
        print(f"Site-packages: {path}")
        
        # Look for NVIDIA packages
        nvidia_path = os.path.join(path, 'nvidia')
        if os.path.exists(nvidia_path):
            print(f"\n✓ NVIDIA packages found at: {nvidia_path}")
            print()
            
            # List subdirectories
            subdirs = [d for d in os.listdir(nvidia_path) if os.path.isdir(os.path.join(nvidia_path, d))]
            print(f"Subdirectories: {subdirs}")
            print()
            
            # Find all DLLs
            for subdir in ['cublas', 'cudnn']:
                subdir_path = os.path.join(nvidia_path, subdir)
                if os.path.exists(subdir_path):
                    print(f"\n{subdir.upper()} structure:")
                    # Search recursively for DLLs
                    dll_pattern = os.path.join(subdir_path, '**', '*.dll')
                    dlls = glob.glob(dll_pattern, recursive=True)
                    
                    if dlls:
                        dll_dirs = set(os.path.dirname(dll) for dll in dlls)
                        for dll_dir in sorted(dll_dirs):
                            dll_files = glob.glob(os.path.join(dll_dir, '*.dll'))
                            print(f"  📁 {dll_dir}")
                            for dll_file in dll_files[:3]:  # Show first 3
                                print(f"     - {os.path.basename(dll_file)}")
                            if len(dll_files) > 3:
                                print(f"     ... and {len(dll_files) - 3} more")
                    else:
                        # List all subdirectories
                        for root, dirs, files in os.walk(subdir_path):
                            print(f"  📁 {root}")
                            if files:
                                for f in files[:3]:
                                    print(f"     - {f}")