from skimage import io
from matplotlib import pyplot as plt
import numpy as np
import os

class Loader:
    def __init__(self, path, outputpath=None, crop_size=128, crop_step=int(128*0.75), total_size=256):
        """
        Crop iterator
        :param path:
        :param crop_size:
        :param crop_step:
        """
        self.path = path
        self.outputpath= outputpath
        self.files = os.listdir(path)

        self.crop_size = crop_size
        self.crop_step = crop_step
        self.total_size = total_size

        self.file_idx = 0
        self.n = 0

        self.generate_crops(os.path.join(self.path, self.files[self.file_idx]))

    def load_image(self, img_path):
        """
        Load the image of the given index, turns it into uint8 RGB for display
        :param file_idx: index of the image in self.files
        :return: Image with shape [height, width, color]
        """
        self.image = io.imread(img_path).astype('float32')
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
                self.crop_data.append({'image':img_path, 'Y':j, 'X':i, 'size':self.crop_size})

        np.random.shuffle(self.crop_data)

    def __iter__(self):
        return self

    def __next__(self):

        if self.n >= len(self.crop_data):
            self.file_idx += 1
            self.x = 0
            self.y = 0
            if self.file_idx < len(self.files):
                self.n = 0
                self.generate_crops(os.path.join(self.path, self.files[self.file_idx]))

        if self.file_idx >= len(self.files):
            #print("Stop iteration ")
            raise StopIteration


        crop = self.crop_data[self.n]
        y = crop['Y']
        x = crop['X']
        size = crop['size']

        pad_size = (self.total_size - self.crop_size)//2
        n_pad = ((pad_size, pad_size), (pad_size, pad_size), (0, 0))
        image_pad = np.pad(self.image, n_pad, mode='constant')

        crop = image_pad[y-pad_size:y+size+pad_size, x-pad_size:x+size+pad_size].copy()
        if crop.shape[0] != crop.shape[1]:
            canvas = np.zeros((self.total_size, self.total_size, 3), dtype='uint8')
            canvas[:crop.shape[0], :crop.shape[1], :] = crop
            crop = canvas

        self.n += 1

        return crop

    def save_patch(self,image, classes, labelling_time=0, ext=None):
        print("Image ", image.shape)
        orig_fname=os.path.join(self.path, self.files[self.file_idx])
        orig_fname_spplit= os.path.splitext(self.files[self.file_idx])
        if ext is None:
            ext=str(orig_fname_spplit[0])
        io.imsave(os.path.join(self.outputpath, str(orig_fname_spplit[0])+'_'+str(self.n)+'.'+ext), image)
        with open(os.path.join(self.outputpath,"patchlist.txt"), "a") as file_object:
            file_object.write(os.path.join(self.outputpath, str(orig_fname_spplit[0])+'_'+str(self.n)+'.'+ext)+";"+str(classes)+";"+labelling_time+"\n")

    def save_crop_data(self, classes, labelling_time, structure):
        orig_fname= os.path.join(self.path, self.files[self.file_idx])
        orig_fname_spplit= os.path.splitext(self.files[self.file_idx])
        if len(self.crop_data)>self.n-1:
            with open(os.path.join(self.outputpath,"patchlist.txt"), "a") as file_object:
                file_object.write(orig_fname+";"+str(self.crop_data[self.n-1]['X'])+";"+str(self.crop_data[self.n-1]['Y'])+";"+str(self.crop_data[self.n-1]['size'])+";"+str(structure)+";"+str(classes)+";"+labelling_time+"\n")

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
