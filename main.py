from FAT32 import FAT32,FAT
from MainUI import MainUI
import os

if __name__ == "__main__":  
    volumes = [chr(x) + ":" for x in range(65, 91) if os.path.exists(chr(x) + ":")]
    print("Available volumes:")
    for i in range(len(volumes)):
        print(f"{i + 1}/", volumes[i])
    try:
        choice = int(input("Which volume to use: "))
    except Exception as e:
        print(f"[ERROR] {e}")
        exit()

    if choice <= 0 or choice > len(volumes):
        print("[ERROR] Invalid choice!")
        exit()
    print()

    volume_name = volumes[choice - 1]
    if FAT32.check_fat32(volume_name):
        vol = FAT32(volume_name)
        print(vol)
        ui = MainUI (vol)
        ui.run()
    else:
        print("[ERROR] Unsupported volume type")
        exit()
    
    

# if __name__ == "__main__":
#     elements = []
#     fd = open(r'\\.\%s' % 'D:', 'rb') ## mở ổ đĩa
#     a = fd.read(0x200)
#     print (a)
#     for i in range(0, len(a), 4):
#         elements.append(int.from_bytes(a[i:i + 4], byteorder='little'))
#     for i in elements:
#         print(i)