from FAT32 import FAT32
import sys
class MainUI:

    def __init__(self,volume: FAT32) -> None:
        self.vol = volume

    def run(self):
        while True:
            print('Curent directory: ')
            print (self.vol.get_cwd())
            self.menu2()
            print('Enter 0 to exit')
            path = input ("Enter path: ")

            if (path == '0'):
                print('Bye bye')
                break

            if (path[-3:] == 'txt'):
                self.menu4(path)
            else: self.menu3(path)
            # self.display_menu()
            # choice = int(input("Enter your choice (0-21): "))

            # if choice == 0:
            #     self.menu0()
            #     break
            # elif 1 <= choice <= 9:
            #     self.handle(choice)
            # else:
            #     print("Invalid choice. Please try again.")

    def display_menu(self):
        return
        # print("         ---FILE SYSTEM---")
        # print("""
        #  1. Print current working directory
        #  2. List out all files and folders in current dir
        #  3. Change to directory 
        #  4. Read a text file
        #  5. 
        #  6. 
        #  7. 
        #  8. 
        #  9. 
        #  0. Exit""")

    def handle (self, choice):
        if choice == 1:
            self.menu1()
        elif choice == 2:
            self.menu2()
        elif choice == 3:
            self.menu3()
        elif choice == 4:
            self.menu4()
        elif choice == 5:
            self.menu5()
        elif choice == 6:
            self.menu6()

    def menu0(self):
        print("BYE...BYE...")
        sys.exit()  

    def menu1(self):
        print (self.vol.get_cwd())

    def menu2(self):
        try:
            filelist = self.vol.get_dir()
            print(f"{'Attri':<10}  {'Sector':>10}  {'LastWriteTime':<20}  {'Length':>12}  {'Name'}")
            print(f"{'─────':<10}  {'──────':>10}  {'─────────────':<20}  {'──────':>12}  {'────'}")
            for file in filelist:
                flags = file['Flags']
                flagstr = list("-------")
                if flags & 0b1:
                    flagstr[-1] = 'r'
                if flags & 0b10:
                    flagstr[-2] = 'h'
                if flags & 0b100:
                    flagstr[-3] = 's'
                if flags & 0b1000:
                    flagstr[-4] = 'v'
                if flags & 0b10000:
                    flagstr[-5] = 'd'
                if flags & 0b100000:
                    flagstr[-6] = 'a'
                flagstr = "".join(flagstr)

                print(f"{flagstr:<10}  {file['Sector']:>10}  {str(file['Date Modified']):<20}  {file['Size'] if file['Size'] else '':>12}  {file['Name']}")
        except Exception as e:
            print(f"[ERROR] {e}")
            
        return

    def menu3(self,path):
        try:
            self.vol.change_dir(path)
            print (self.vol.get_cwd())

        except Exception as e:
            print(f'{e}')

    def menu4(self,path):
        try:
            data = self.vol.get_text_file(path)
            print(data)
        except Exception as e:
            print(f'{e}')
        
    
    def menu5(self):
        
        return
    
    def menu6(self):
        return