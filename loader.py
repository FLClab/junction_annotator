from skimage import io
from skimage.filters import threshold_triangle, gaussian, rank
from skimage.morphology import binary_erosion, area_closing, binary_dilation
from scipy.ndimage.morphology import binary_fill_holes
import numpy as np
import os
import json
from datetime import datetime

from matplotlib import pyplot as plt


HISTORY_F_NAME= os.path.join(os.path.dirname(os.path.abspath(__file__)),"history.json")
OUTPUT_FILE_NAME="patchlist.txt"

class Loader:
    
    def __init__(self, path, outputpath=None, crop_size=60, crop_step=int(60*0.75), total_size=128, fg_threshold=0.2):
        """
        Crop iterator
        :param path:
        :param crop_size: Size of the crop of interest
        :param crop_step: Step between crops; smaller step means larger overlap between crops
        :param total_size: Size of the larger crop for vizualisation
        :param fg_threshold: Proportion of the crop that must be foreground to be considered
        """
        self.path = path
        self.outputpath= outputpath
        self.files = os.listdir(path)

        self.crop_size = crop_size
        self.crop_step = crop_step
        self.total_size = total_size

        self.fg_threshold = fg_threshold

        self.file_idx = 0
        self.n = 0
        self.previous= 0
        self.atStopIteration= False

        self.generate_crops(os.path.join(self.path, self.files[self.file_idx]))

    def load_image(self, img_path, edges=True):
        """
        Load the image of the given index, turns it into uint8 RGB for display
        :param file_idx: index of the image in self.files
        :return: Image with shape [height, width, color]
        """
        self.image = io.imread(img_path).astype('float32')

        # Get a vague segmentation of the foreground
        background = self.image[1]
        background = background < np.percentile(background, 50)
        background = gaussian(background, 5) > 0.3
        foreground = binary_fill_holes(1 - background)

        # Get the difference of the foreground and an eroded foreground as edge
        if edges:
            foreground_erode = rank.minimum((foreground * 1).astype('uint8'), np.ones((256, 256)))  # Here we can vary the thickness of the edges with the shape of the np.ones
            foreground = foreground - foreground_erode

        self.foreground = foreground

        #print("image ", self.image.shape)
        self.image[0] = self.image[0] - np.min(self.image[0], axis=0)
        self.image[1] = self.image[1] - np.min(self.image[1], axis=0)
        self.image[0] = self.image[0] / np.percentile(self.image[0], 99.9)
        self.image[1] = self.image[1] / np.percentile(self.image[1], 99.9)
        self.image = np.clip(self.image, 0, 1)
        self.image = (self.image*255).astype('uint8')

        self.image = np.concatenate((self.image, np.zeros((1,self.image.shape[1], self.image.shape[2]), dtype='uint8')), axis=0)
        self.image = np.moveaxis(self.image, 0, -1)
        buffer = self.image[:,:,1].copy()
        self.image[:,:,1] = self.image[:,:,0].copy()
        self.image[:,:,0] = buffer
        #print("image after ", self.image.shape)

    def generate_crops(self, img_path):
        #print("Generating crop for ", img_path )
        self.load_image(img_path)
        self.crop_data = []
        for j in range(0, self.image.shape[0], self.crop_step):
            for i in range(0, self.image.shape[1], self.crop_step):
                # Check if crop contains significant foreground
                crop = self.foreground[j:j+self.crop_size, i:i+self.crop_size]
                if np.sum(crop) >= np.size(crop) * 0.10:
                    self.crop_data.append({'image':img_path, 'Y':j, 'X':i, 'size':self.crop_size})

        #self.crop_data = self.crop_data[1:]
        np.random.shuffle(self.crop_data)

    def __iter__(self):
        return self

    def __next__(self):
        self.previous =0
        self.atStopIteration= False
        if self.n >= len(self.crop_data):
            self.file_idx += 1
            self.x = 0
            self.y = 0
            if self.file_idx < len(self.files):
                self.n = 0
                self.generate_crops(os.path.join(self.path, self.files[self.file_idx]))

        if self.file_idx >= len(self.files):
            #print("Stop iteration ")
            self.atStopIteration = True
            raise StopIteration


        crop = self.crop_data[self.n]
        y = crop['Y']
        x = crop['X']
        size = crop['size']

        pad_size = (self.total_size - self.crop_size)//2
        n_pad = ((pad_size, pad_size), (pad_size, pad_size), (0, 0))
        image_pad = np.pad(self.image, n_pad, mode='constant')

        crop = image_pad[y:y+size+2*pad_size, x:x+size+2*pad_size].copy()
        if crop.shape[0] != crop.shape[1]:
            canvas = np.zeros((self.total_size, self.total_size, 3), dtype='uint8')
            canvas[:crop.shape[0], :crop.shape[1], :] = crop
            crop = canvas

        self.n += 1

        return crop

    def __previous__(self):
        self.previous = self.previous- 1
        self.n = self.n - 2
        if self.n < 0 :
            self.n = self.n + 2
            self.previous= 0
            return None 
            #self.file_idx -= 1
            #self.x = 0
            #self.y = 0
            #if self.file_idx < len(self.files):    
            #    self.generate_crops(os.path.join(self.path, self.files[self.file_idx]))
            #    self.n = len( self.crop_data) -1
        #if self.file_idx >= len(self.files):
        #    #print("Stop iteration ")
        #    raise StopIteration


        crop = self.crop_data[self.n]
        y = crop['Y']
        x = crop['X']
        size = crop['size']
    
        pad_size = (self.total_size - self.crop_size)//2
        n_pad = ((pad_size, pad_size), (pad_size, pad_size), (0, 0))
        image_pad = np.pad(self.image, n_pad, mode='constant')

        crop = image_pad[y:y+size+2*pad_size, x:x+size+2*pad_size].copy()
        if crop.shape[0] != crop.shape[1]:
            canvas = np.zeros((self.total_size, self.total_size, 3), dtype='uint8')
            canvas[:crop.shape[0], :crop.shape[1], :] = crop
            crop = canvas

        self.n += 1
        self.atStopIteration= False

        return crop
 
    def save_patch(self,image, classes, labelling_time=0, ext=None):
        print("Image ", image.shape)
        orig_fname=os.path.join(self.path, self.files[self.file_idx])
        orig_fname_spplit= os.path.splitext(self.files[self.file_idx])
        if ext is None:
            ext=str(orig_fname_spplit[0])
        io.imsave(os.path.join(self.outputpath, str(orig_fname_spplit[0])+'_'+str(self.n)+'.'+ext), image)
        with open(os.path.join(self.outputpath,OUTPUT_FILE_NAME), "a") as file_object:
            file_object.write(os.path.join(self.outputpath, str(orig_fname_spplit[0])+'_'+str(self.n)+'.'+ext)+";"+str(classes)+";"+labelling_time+"\n")

    def save_crop_data(self, classes, labelling_time, structure, ambiguous):
        orig_fname= os.path.join(self.path, self.files[self.file_idx])
        orig_fname_spplit= os.path.splitext(self.files[self.file_idx])
        if len(self.crop_data)>self.n-1:
            if self.previous>=0:
                with open(os.path.join(self.outputpath,OUTPUT_FILE_NAME), "a") as file_object:
                    file_object.write(orig_fname+";"+str(self.crop_data[self.n-1]['X'])+";"+str(self.crop_data[self.n-1]['Y'])+";"+str(self.crop_data[self.n-1]['size'])+";"+str(structure)+";"+str(classes)+";"+str(ambiguous)+";"+labelling_time+"\n")
            else:
                lines = open(os.path.join(self.outputpath,OUTPUT_FILE_NAME), 'r').readlines()
                lines = lines[:self.previous]
                lines.append(orig_fname+";"+str(self.crop_data[self.n-1]['X'])+";"+str(self.crop_data[self.n-1]['Y'])+";"+str(self.crop_data[self.n-1]['size'])+";"+str(structure)+";"+str(classes)+";"+labelling_time+"\n")
                open(os.path.join(self.outputpath,OUTPUT_FILE_NAME), 'w').writelines(lines)
                self.previous= 0


    def saveHistory(self, classes=[], structures=[]):
        #☺ ne pas sauvegarder si l'utilisateur a parcouru dejà toutes les images
        self.deleteHistory()
        if self.atStopIteration:
            return
        f_ow = open(HISTORY_F_NAME, "w")
        last_data={"path":self.path, "outputpath":self.outputpath, 
                   "file_idx":self.file_idx, "files":self.files, 
                   "crop_data":self.crop_data, "n":self.n-1,
                   "classes":classes, "structures":structures }
        json.dump(last_data, f_ow)
        f_ow.close()
        #with open(HISTORY_F_NAME, "w") as file_object:
        
    #@classmethod
    #def loadHistory(cls, crop_size, crop_step, total_size):
    @staticmethod
    def loadFromHistory( crop_size, crop_step, total_size):
        mloader= None
        if os.path.exists(HISTORY_F_NAME):
            with open(HISTORY_F_NAME) as json_file:
                data = json.load(json_file)
                mloader = Loader( path=data["path"], outputpath=data["outputpath"], crop_size=crop_size, crop_step=crop_step, total_size=total_size) 
                #mloader.path = data["path"]
                #mloader.outputpath= data["outputpath"]
                if os.path.exists(os.path.join( data["outputpath"],OUTPUT_FILE_NAME)):
                    mloader.file_idx= data["file_idx"]
                    mloader.files= data["files"]
                    mloader.crop_data= data["crop_data"]
                    mloader.n= data["n"]
                    classes=data["classes"]
                    structures=data["structures"]                
                    mloader.load_image(os.path.join(mloader.path, mloader.files[mloader.file_idx]))#  mloader.generate_crops(os.path.join(mloader.path, mloader.files[mloader.file_idx]))
            #return mloader
        return mloader
            
    def deleteHistory(self):
        if os.path.exists(HISTORY_F_NAME):
            os.remove(HISTORY_F_NAME)
            
    def renamePatchListFile(self):
        if os.path.exists(os.path.join(self.outputpath,OUTPUT_FILE_NAME)):
            fnamepath=os.path.join(self.outputpath,OUTPUT_FILE_NAME)
            fnamesplit = os.path.splitext(OUTPUT_FILE_NAME)
            fnewnamepath=os.path.join(self.outputpath,fnamesplit[0]+"_"+datetime.now().strftime("%Y%m%d%H%M%S")+"."+fnamesplit[1] )        
            os.rename(fnamepath, fnewnamepath)
            #os.remove(HISTORY_F_NAME)
        
def generate_box(crop_size=128, total_size=256):
    """
    Generate the focus box in the center
    """
    pad_size = (total_size - crop_size) // 2
    box = np.zeros((total_size,total_size,3)).astype('bool')
    box[pad_size-3:pad_size+crop_size+3, pad_size-3:pad_size+crop_size+3, (1,2)] = True
    box[pad_size:pad_size+crop_size, pad_size:pad_size+crop_size, (1,2)] = False

    return box

if __name__=='__main__':
    data_path = 'example_image'
    out_path = 'outdir_image'
    os.makedirs(out_path, exist_ok=True)
    loader = Loader(path=data_path, outputpath=out_path)
    for l in loader:
        loader.save_patch(l, [0,0,2,3], 'png')
        pass
