import os
import string
import configparser

class TadpoleConfig():
    _static_TadpoleFolder = os.path.join(os.path.expanduser('~'), '.tadpole')
    _static_TadpoleConfigFile = os.path.join(_static_TadpoleFolder, 'tadpole.ini')
    # [tadpole]
    _static_general = "tadpole"
    _static_general_userDirectory = "user_directory"
    _static_general_userDirectory_DEFAULT = ""
    _static_general_tadpole_version = "current_tadpole_version"
    _static_general_tadpole_version_DEFAULT = "0.5"
    # [thumbnails]
    _static_thumbnails = "Thumbnails"
    _static_thumbnails_view = "ViewInTable"
    _static_thumbnails_view_DEFAULT = "False"
    _static_thumbnails_overwrite = "overwrite"
    _static_thumbnails_overwrite_DEFAULT = "False"
    _static_thumbnails_download = "download"
    _static_thumbnails_download_DEFAULT = "0"

    
    def __init__(self):
        super().__init__()
        print(f"establishing tadpole config")
        self.config = configparser.ConfigParser()
        #if not os.path.exists(self._static_TadpoleFolder):
        #    os.makedirs(self._static_TadpoleFolder, exist_ok=True)
        # Check if config file exists on the device
        if not os.path.exists(self._static_TadpoleConfigFile):
            #Config file not found, create a new one            
            with open(self._static_TadpoleConfigFile, 'w') as newConfigFile:
                self.config.write(newConfigFile)
          
        # Double check that the config file now exists
        if not os.path.exists(self._static_TadpoleConfigFile):
            #TODO replace this with a proper exception
            raise Exception
          
        #open the config  
        self.config.read(self._static_TadpoleConfigFile)
          
        # make sure all the right keys exist, if not create the defaults
        # [Tadpole]
        if not self.config.has_section(self._static_general):
            self.config[self._static_general] = {}
        if not self.config.has_option(self._static_general, self._static_general_userDirectory):
            self.config[self._static_general][self._static_general_userDirectory] = self._static_general_userDirectory_DEFAULT
        if not self.config.has_option(self._static_general, self._static_general_tadpole_version):
            self.config[self._static_general][self._static_general_tadpole_version] = self._static_general_tadpole_version_DEFAULT
        # [Thumbnails]
        if not self.config.has_section(self._static_thumbnails):
            self.config[self._static_thumbnails] = {}
        if not self.config.has_option(self._static_thumbnails, self._static_thumbnails_view):
            self.config[self._static_thumbnails][self._static_thumbnails_view] = self._static_thumbnails_view_DEFAULT
        if not self.config.has_option(self._static_thumbnails, self._static_thumbnails_overwrite):
            self.config[self._static_thumbnails][self._static_thumbnails_overwrite] = self._static_thumbnails_overwrite_DEFAULT
        
        
        # Update the config out to file
        with open(self._static_TadpoleConfigFile, 'w') as newConfigFile:
            self.config.write(newConfigFile)
    
    def setVariable(self, section, option, value):
        #Check the section exists, if it doesnt then create it
        if not self.config.has_section(section):
            self.config[section] = {}
        self.config[section][option] = value
        with open(self._static_TadpoleConfigFile, 'w') as newConfigFile:
            self.config.write(newConfigFile)
            
    def getVariable(self, section, option, default):
        if (self.config.has_option(section,option)):
            return self.config[section][option]
        print(f"Returning default for ({section})({option})")
        return default
    
    def setLocalUserDirectory(self, location):
        print(f"Setting LocalUserDirectory to ({location})")
        self.setVariable(self._static_general, self._static_general_userDirectory, location)
                
    """
    Checks if the user_directory value has been set in the tadpole section
    If it has then the value is returned
    If it hasnt then the default value is returned
    """
    def getLocalUserDirectory(self):
        return self.getVariable(self._static_general,self._static_general_userDirectory,self._static_general_userDirectory_DEFAULT)

    def getCurrentTadpoleVersion(self):
        return self.getVariable(self._static_general,self._static_general_tadpole_version,self._static_general_tadpole_version)

    def setCurrentTadpoleVersion(self):
        print(f"Setting setCurrentTadpoleVersion")
        self.setVariable(self._static_general, self._static_general_tadpole_version, self._static_general_tadpole_version_DEFAULT)
    
    def setViewThumbnailsInTable(self, enabled: bool):
        print(f"Setting ViewThumbnailsInTable to ({enabled})")
        self.setVariable(self._static_thumbnails, self._static_thumbnails_view, ("True" if enabled else "False"))
    
    def getViewThumbnailsInTable(self):
        view = self.getVariable(self._static_thumbnails,self._static_thumbnails_view,self._static_general_userDirectory_DEFAULT)
        return view == "True"

    def setThumbnailDownload(self, enabled: bool):
        print(f"Setting ThumbnailDownload to ({enabled})")
        self.setVariable(self._static_thumbnails, self._static_thumbnails_download, ("1" if enabled else "0"))
    
    def getThumbnailDownload(self):
        view = self.getVariable(self._static_thumbnails,self._static_thumbnails_download,self._static_thumbnails_download_DEFAULT)
        return view == "1"

    def setThumbnailOverwrite(self, enabled: bool):
        print(f"Setting ThumbnailOverwrite to ({enabled})")
        self.setVariable(self._static_thumbnails, self._static_thumbnails_overwrite, ("True" if enabled else "False"))
    
    def getThumbnailOverwrite(self):
        view = self.getVariable(self._static_thumbnails,self._static_thumbnails_overwrite,self._static_thumbnails_overwrite_DEFAULT)
        return view == "True"