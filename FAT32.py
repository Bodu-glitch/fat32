from enum import Flag, auto
from datetime import datetime
from itertools import chain
import re
import os
class Attribute(Flag):
    READ_ONLY = auto()
    HIDDEN = auto()
    SYSTEM = auto()
    VOLLABLE = auto()
    DIRECTORY = auto()
    ARCHIVE = auto()

class FAT:
  def __init__(self, data) -> None:
    self.raw_data = data
    self.elements = []

    #1 elements là 1 int lấy ra từ data có 4 bytes (32bits)
    for i in range(0, len(self.raw_data), 4):
      self.elements.append(int.from_bytes(self.raw_data[i:i + 4], byteorder='little'))

  ## Lấy chuỗi cluster (mỗi phần tử trong 
  ## elements sẽ có data băng index tiếp theo kết thúc ở 0x0FFFFFFF hoặc 0x0FFFFFF7)
  def get_cluster_chain(self, index: int) -> 'list[int]':
    index_list = []
    while True:
      index_list.append(index)
      index = self.elements[index]
      if index == 0x0FFFFFFF or index == 0x0FFFFFF7:
        break
    return index_list 

class RDETentry:
  def __init__(self, data) -> None:
    self.raw_data = data
    self.flag = data[0xB:0xC]
    self.is_subentry: bool = False ## biến này để xác định đây có phải là file có tên dài hay không
    self.is_deleted: bool = False ## 
    self.is_empty: bool = False ##
    self.is_label: bool = False ## ktra xem phải ổ đĩa kh
    self.attr = Attribute(0)
    self.size = 0
    self.date_created = 0
    self.last_accessed = 0
    self.date_updated = 0
    self.ext = b""
    self.long_name = ""
    if self.flag == b'\x0f': ## nếu biến cờ là 0x0F thì là file có tên dài (LFN)
      self.is_subentry = True 

    if not self.is_subentry: ## không phải file có tên dài
      self.name = self.raw_data[:0x8] ## 8 byte đầu tiên
      self.ext = self.raw_data[0x8:0xB] ## 3 byte kế
      if self.name[:1] == b'\xe5':  ## kiểm tra xem file có xóa không khi xóa thì gán 0xe5 vào cho bit đầu tiên
        self.is_deleted = True
      if self.name[:1] == b'\x00': ## byte đầu là 0 thì là rỗng
        self.is_empty  = True
        self.name = ""
        return
      
      self.attr = Attribute(int.from_bytes(self.flag, byteorder='little'))
      if Attribute.VOLLABLE in self.attr: ##
        self.is_label = True
        return
      
##time(h,m,s), date(d,mon,y), lastaccess(d,mon,y) 
      self.time_created_raw = int.from_bytes(self.raw_data[0xD:0x10], byteorder='little') ## 3byte =24 bit
      self.date_created_raw = int.from_bytes(self.raw_data[0x10:0x12], byteorder='little') ## 2 byte = 16 bit
      self.last_accessed_raw = int.from_bytes(self.raw_data[0x12:0x14], byteorder='little') ## 2 byte = 16 bit

##giờ file thực hiện thao tác ghi (time và date)
      self.time_updated_raw = int.from_bytes(self.raw_data[0x16:0x18], byteorder='little') ##2byte
      self.date_updated_raw = int.from_bytes(self.raw_data[0x18:0x1A], byteorder='little') ##2byte


      h = (self.time_created_raw & 0b111110000000000000000000) >> 19 ## 23->19 5 bit đầu tiên giữ lại (phép end) thể hiện cho giờ
      m = (self.time_created_raw & 0b000001111110000000000000) >> 13 ## 18->13 6 bit tiếp (m)
      s = (self.time_created_raw & 0b000000000001111110000000) >> 7  ## 12 -> 7
      ms =(self.time_created_raw & 0b000000000000000001111111)

      year = 1980 + ((self.date_created_raw & 0b1111111000000000) >> 9) ## 15->9  1980 + 2^7 -1
      mon = (self.date_created_raw & 0b0000000111100000) >> 5 ## 9->5
      day = self.date_created_raw & 0b0000000000011111

      self.date_created = datetime(year, mon, day, h, m, s, ms)

      year = 1980 + ((self.last_accessed_raw & 0b1111111000000000) >> 9)
      mon = (self.last_accessed_raw & 0b0000000111100000) >> 5
      day = self.last_accessed_raw & 0b0000000000011111

      self.last_accessed = datetime(year, mon, day)

      h = (self.time_updated_raw & 0b1111100000000000) >> 11
      m = (self.time_updated_raw & 0b0000011111100000) >> 5
      s = (self.time_updated_raw & 0b0000000000011111) * 2
      year = 1980 + ((self.date_updated_raw & 0b1111111000000000) >> 9)
      mon = (self.date_updated_raw & 0b0000000111100000) >> 5
      day = self.date_updated_raw & 0b0000000000011111

      self.date_updated = datetime(year, mon, day, h, m, s)

##fisrt cluster high + frist cluster low = starting cluster
      self.start_cluster = int.from_bytes(self.raw_data[0x14:0x16] [::-1] + self.raw_data[0x1A:0x1C] [::-1], byteorder='big') 
      self.size = int.from_bytes(self.raw_data[0x1C:0x20], byteorder='little') ## lấy size

    else: ## subentry = true (LFN)
      self.index = self.raw_data[0]
      self.name = b""
      ## (0x1, 0xB): tên 1, (0xE,0x1A): tên 2, (0x1C, 0x20): tên 3
      for i in chain(range(0x1, 0xB), range(0xE, 0x1A), range(0x1C, 0x20)):
        self.name += int.to_bytes(self.raw_data[i], 1, byteorder='little')
        if self.name.endswith(b"\xff\xff"): ## nếu gặp 0xff thì break
          self.name = self.name[:-2]  ## name bỏ 2 giá trị ff
          break
      self.name = self.name.decode('utf-16le').strip('\x00')

# các hàm kiểm tra qua biến cờ
  def is_active_entry(self) -> bool:
    return not (self.is_empty or self.is_subentry or self.is_deleted or self.is_label or Attribute.SYSTEM in self.attr)
  
  def is_directory(self) -> bool:
    return Attribute.DIRECTORY in self.attr

  def is_archive(self) -> bool:
    return Attribute.ARCHIVE in self.attr
  
  
  
# bảng RDET
class RDET:
  def __init__(self, data: bytes) -> None:
    self.raw_data: bytes = data
    self.entries: list[RDETentry] = []
    long_name = "" ## biến này để gộp name vs ext

    # 1 entry trong bảng có 32 byte
    for i in range(0, len(data), 32):
      self.entries.append(RDETentry(self.raw_data[i: i + 32]))

      ## entries[-1] là entry mới được thêm vào
      if self.entries[-1].is_empty or self.entries[-1].is_deleted:
        long_name = ""
        continue

      
      if self.entries[-1].is_subentry: ## nêu subentry được bật (LFN)
        long_name = self.entries[-1].name + long_name
        continue

      if long_name != "": ## đã thêm tên vào
        self.entries[-1].long_name = long_name ## thêm RDET.ln vào Entri.ln
      else: # không phải lfn
        extend = self.entries[-1].ext.strip().decode()
        if extend == "":
          self.entries[-1].long_name = self.entries[-1].name.strip().decode()
        else:
          self.entries[-1].long_name = self.entries[-1].name.strip().decode() + "." + extend # gộp tên và ext
      long_name = ""

## lấy các entries đang active
  def get_active_entries(self) -> 'list[RDETentry]':
    entry_list = []
    for i in range(len(self.entries)):
      if self.entries[i].is_active_entry():
        entry_list.append(self.entries[i])
    return entry_list
## tìm qua tên
  def find_entry(self, name) -> RDETentry:
    for i in range(len(self.entries)):
      if self.entries[i].is_active_entry() and self.entries[i].long_name.lower() == name.lower():
        return self.entries[i]
    return None
  
  def __str__(self) -> str:
    for i in self.entries:
      print(f'{i.name}')

class FAT32:
  important_info = [
    "OEMname",
    "Bytes Per Sector",
    "Sectors Per Cluster", 
    "Reserved Sectors", 
    "Sectors Per FAT",
    "No. Copies of FAT",
    "No. Sectors In Volume",
    "Starting Cluster of RDET",
    "Starting Sector of Data",
    "FAT Name"
  ]
  def __init__(self, name: str) -> None:
    self.name = name
    self.cwd = [self.name] # giữ vị trí hiện tại, bỏ ổ đĩa vào đầu tiên
    try:
      self.fd = open(r'\\.\%s' % self.name, 'rb') ## mở ổ đĩa
    except FileNotFoundError:
      print(f"[ERROR] No volume named {name}")
      exit() 
    except PermissionError:
      print("[ERROR] Permission denied, try again as admin/root")
      exit()
    except Exception as e:
      print(e)
      print("[ERROR] Unknown error occurred")
      exit() 
    
    try:
      self.boot_sector_raw = self.fd.read(0x200) # đọc 512 byte đầu tiên 
      self.boot_sector = {} ## dictionary
      self.__extract_boot_sector()
      if self.boot_sector["FAT Name"] != b"FAT32   ":
        raise Exception("Not FAT32")
      self.boot_sector["FAT Name"] = self.boot_sector["FAT Name"].decode()
      self.SB = self.boot_sector['Reserved Sectors']
      self.SF = self.boot_sector["Sectors Per FAT"]
      self.NF = self.boot_sector["No. Copies of FAT"]
      self.SC = self.boot_sector["Sectors Per Cluster"]
      self.BS = self.boot_sector["Bytes Per Sector"]
      self.boot_sector_reserved_raw = self.fd.read(self.BS * (self.SB - 1)) ## đọc vùng lưu trữ (-1 là trừ cái boot sector mới đọc)
      # self.boot_sector["OEMname"] = self.boot_sector["OEMname"].decode()
      
      FAT_size = self.BS * self.SF ## size 1 bảng fat
      ##FAT32.FAT là cái bảng FAT
      self.FAT: list[FAT] = []
      for _ in range(self.NF):
        self.FAT.append(FAT(self.fd.read(FAT_size))) ## đọc tiếp phần FAT

      self.DET = {}
      
      start = self.boot_sector["Starting Cluster of RDET"] ## đây là cluster bắt đầu của bảng direntry
      self.DET[start] = RDET(self.get_all_cluster_data(start))
      self.RDET = self.DET[start]  

    except Exception as e:
      print(f"[ERROR] {e}")
      exit()
  
  @staticmethod
  def check_fat32(name: str):
    try:
      with open(r'\\.\%s' % name, 'rb') as fd:
        fd.read(1)
        fd.seek(0x52) ## file system type offset 0x52
        fat_name = fd.read(8)
        if fat_name == b"FAT32   ":
          return True
        return False
    except Exception as e:
      print(f"[ERROR] {e}")
      exit()

  def __extract_boot_sector(self):
    self.boot_sector["OEMname"] = self.boot_sector_raw[0x3:0xB]
    # self.boot_sector['Jump_Code'] = self.boot_sector_raw[:3]
    # self.boot_sector['OEM_ID'] = self.boot_sector_raw[3:0xB]
    self.boot_sector['Bytes Per Sector'] = int.from_bytes(self.boot_sector_raw[0xB:0xD], byteorder='little')
    self.boot_sector['Sectors Per Cluster'] = int.from_bytes(self.boot_sector_raw[0xD:0xE], byteorder='little')
    self.boot_sector['Reserved Sectors'] = int.from_bytes(self.boot_sector_raw[0xE:0x10], byteorder='little')
    self.boot_sector['No. Copies of FAT'] = int.from_bytes(self.boot_sector_raw[0x10:0x11], byteorder='little')
    # self.boot_sector['Media Descriptor'] = self.boot_sector_raw[0x15:0x16]
    # self.boot_sector['Sectors Per Track'] = int.from_bytes(self.boot_sector_raw[0x18:0x1A], byteorder='little')
    # self.boot_sector['No. Heads'] = int.from_bytes(self.boot_sector_raw[0x1A:0x1C], byteorder='little')
    self.boot_sector['No. Sectors In Volume'] = int.from_bytes(self.boot_sector_raw[0x20:0x24], byteorder='little')
    self.boot_sector['Sectors Per FAT'] = int.from_bytes(self.boot_sector_raw[0x24:0x28], byteorder='little')
    self.boot_sector['Flags'] = int.from_bytes(self.boot_sector_raw[0x28:0x2A], byteorder='little')
    self.boot_sector['FAT32 Version'] = self.boot_sector_raw[0x2A:0x2C]
    self.boot_sector['Starting Cluster of RDET'] = int.from_bytes(self.boot_sector_raw[0x2C:0x30], byteorder='little')
    # self.boot_sector['Sector Number of the FileSystem Information Sector'] = self.boot_sector_raw[0x30:0x32]
    # self.boot_sector['Sector Number of BackupBoot'] = self.boot_sector_raw[0x32:0x34]
    self.boot_sector['FAT Name'] = self.boot_sector_raw[0x52:0x5A]
    # self.boot_sector['Executable Code'] = self.boot_sector_raw[0x5A:0x1FE]
    # self.boot_sector['Signature'] = self.boot_sector_raw[0x1FE:0x200]
    self.boot_sector['Starting Sector of Data'] = self.boot_sector['Reserved Sectors'] + self.boot_sector['No. Copies of FAT'] * self.boot_sector['Sectors Per FAT']

  ## trả vè offset của index
  def __offset_from_cluster(self, index):
    return self.boot_sector['Starting Sector of Data'] + (index - 2) * self.SC ## vùng data bắt đầu từ số 2
  
  def __parse_path(self, path): ## trả về mảng string với từng \\ là một phần tử qua hàm split
    dirs = re.sub(r"[/\\]+", r"\\", path).strip("\\").split("\\")
    return dirs

  def get_cwd(self): #trả về cái đường dẫn qua self.cwd
    if len(self.cwd) == 1:
      return self.cwd[0] + "\\"
    return "\\".join(self.cwd)

  def visit_dir(self, dir) -> RDET: # 
    if dir == "":
      raise Exception("Directory name is required!")
    dirs = self.__parse_path(dir)

    if dirs[0] == self.name:
      cdet = self.DET[self.boot_sector["Starting Cluster of RDET"]]
      dirs.pop(0)
    else:
      cdet = self.RDET

    for d in dirs:
      entry = cdet.find_entry(d)
      if entry is None:
        raise Exception("Directory not found!")
      if entry.is_directory():
        if entry.start_cluster == 0:
          cdet = self.DET[self.boot_sector["Starting Cluster of RDET"]]
          continue
        if entry.start_cluster in self.DET:
          cdet = self.DET[entry.start_cluster]
          continue
        self.DET[entry.start_cluster] = RDET(self.get_all_cluster_data(entry.start_cluster))
        cdet = self.DET[entry.start_cluster] 
      else:
        raise Exception("Not a directory")
    return cdet
  
  def change_dir(self, path=""): ## xử lí cwd
    if path == "":
      raise Exception("Path to directory is required!")
    try:
      cdet = self.visit_dir(path) #return entry table/ curent entry 
      self.RDET = cdet

      dirs = self.__parse_path(path)  
      if dirs[0] == self.name:
        self.cwd.clear()
        self.cwd.append(self.name)
        dirs.pop(0)
      for d in dirs:
        if d == "..":
          self.cwd.pop()
        elif d != ".":
          self.cwd.append(d)
    except Exception as e:
      raise(e)
    
  def get_dir(self, dir=""): 
    try:
      if dir != "":
        cdet = self.visit_dir(dir)
        entry_list = cdet.get_active_entries()
      else:
        entry_list = self.RDET.get_active_entries()
      ret = []
      for entry in entry_list:
        obj = {}
        obj["Flags"] = entry.attr.value
        obj["Date Modified"] = entry.date_updated
        obj["Size"] = entry.size
        obj["Name"] = entry.long_name
        if entry.start_cluster == 0:
          obj["Sector"] = (entry.start_cluster + 2) * self.SC
        else:
          obj["Sector"] = entry.start_cluster * self.SC
        ret.append(obj)
      return ret #trả về mảng các entry lấy thông tin
    except Exception as e:
      raise(e)

  def get_all_cluster_data(self, cluster_index):
    #bảng fat
    index_list = self.FAT[0].get_cluster_chain(cluster_index) 
    data = b""
    for i in index_list:
      off = self.__offset_from_cluster(i) ## trả về offset của i
      self.fd.seek(off * self.BS) ## off * Bs để đổi ra byte 
      data += self.fd.read(self.SC * self.BS) ##đọc
    return data
  
  def get_text_file(self, path: str) -> str:
    path = self.__parse_path(path)
    if len(path) > 1:
      name = path[-1]
      path = "\\".join(path[:-1])
      cdet = self.visit_dir(path) #visit_dir trả về 1 RDET
      entry = cdet.find_entry(name)
    else:
      entry = self.RDET.find_entry(path[0])

    if entry is None:
      raise Exception("File doesn't exist")
    if entry.is_directory():
      raise Exception("Is a directory")
    index_list = self.FAT[0].get_cluster_chain(entry.start_cluster)
    data = ""
    size_left = entry.size
    for i in index_list:
      if size_left <= 0:
        break
      off = self.__offset_from_cluster(i)
      self.fd.seek(off * self.BS)
      raw_data = self.fd.read(min(self.SC * self.BS, size_left)) #1 là đọc hết 2 là đọc đúng size
      size_left -= self.SC * self.BS #đọc xong thì trừ ra
      try:
        data += raw_data.decode()
      except UnicodeDecodeError as e:
        raise Exception("Not a text file, please use appropriate software to open.")
      except Exception as e:
        raise(e)
    return data

  def get_file_content(self, path: str) -> bytes:
    path = self.__parse_path(path)
    if len(path) > 1:
      name = path[-1]
      path = "\\".join(path[:-1])
      cdet = self.visit_dir(path)
      entry = cdet.find_entry(name)
    else: 
      entry = self.RDET.find_entry(path[0])

    if entry is None:
      raise Exception("File doesn't exist")
    if entry.is_directory():
      raise Exception("Is a directory")
    data = self.get_all_cluster_data(entry.start_cluster)[:entry.size]
    return data

  def __str__(self) -> str:
    s = "Volume name: " + self.name
    s += "\nVolume information:\n"
    for key in FAT32.important_info:
      s += f"{key}: {self.boot_sector[key]}\n"
    return s

  def __del__(self):
    if getattr(self, "fd", None):
      print("Closing Volume...")
      self.fd.close()

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
        a = vol.RDET
        print(a)
    else:
        print("[ERROR] Unsupported volume type")
        exit()