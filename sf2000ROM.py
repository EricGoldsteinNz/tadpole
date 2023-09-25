import os

class sf2000ROM():
    ROMlocation = ""
    ROMsecondaryFiles = []
    title = ""
    thumbnail = None
    console = None

    def __init__(self, location):
        super().__init__()
        # Check the file actually exists otherwise throw an error
        if not os.path.isfile(location):
            raise Exception
        self.ROMlocation = location
        #self.title = os.path.splitext(os.path.basename(location))[0]
        self.title = os.path.basename(location)


    """
    Note that this will change the filename as well
    """
    def setTitle(self, newTitle):
        try:
            #ext = os.path.splitext(self.ROMlocation)[1]
            newPath = os.path.join(os.path.dirname(self.ROMlocation),newTitle)
            os.rename(self.ROMlocation, newPath)
            self.ROMlocation = newPath         
            self.title = newTitle
            return True
        except:
            return False

    def getFileSize(self):
        if not os.path.isfile(self.ROMlocation):
            raise Exception
        return os.path.getsize(self.ROMlocation)
        # TODO Add counting multiple files for ARCADE zips