from skimage import io
from matplotlib import pyplot as plt

if __name__=='__main__':
    liste = [line.strip().split(";") for line in open ('patchlist.txt','r')]

    image = io.imread('example_image/F2175j_s5_cldn3_Factin_40X-pic6-ApoTome-10-Stitching-11.czi - F2175j_s5_cldn3_Factin_40X-pic6-ApoTome-10-Stitching-11.czi #1-1.tif')
    plt.imshow(image[1])
    plt.show()
    print(image.shape)
    for l in liste:
        x = int(l[1])
        y = int(l[2])

        plt.imshow(image[1,y:y+64,x:x+64].T)
        plt.show()
        plt.close()