import sys
from PIL import Image, ImageChops
def crop(p, m=25):
    im = Image.open(p).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bb = ImageChops.difference(im, bg).getbbox()
    if bb:
        im.crop((max(bb[0]-m,0), max(bb[1]-m,0), min(bb[2]+m, im.width), min(bb[3]+m, im.height))).save(p)
if __name__ == "__main__":
    for p in sys.argv[1:]: crop(p)
