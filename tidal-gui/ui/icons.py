from PIL import Image, ImageDraw
import customtkinter as ctk

def create_icon(name, size=(20, 20), color="white"):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w, h = size
    p = 2 # Padding
    
    if name == "play":
        draw.polygon([(p+2, p), (p+2, h-p), (w-p, h/2)], fill=color)
    elif name == "pause":
        bw = (w - 2*p) / 3 
        draw.rectangle([(p+2, p), (p+2+bw, h-p)], fill=color)
        draw.rectangle([(w-p-2-bw, p), (w-p-2, h-p)], fill=color)
    elif name == "prev":
        draw.rectangle([(p, p), (p+3, h-p)], fill=color) # Bar
        draw.polygon([(p+5, h/2), (w-p, p), (w-p, h-p)], fill=color) # Triangle Left
    elif name == "next":
        draw.rectangle([(w-p-3, p), (w-p, h-p)], fill=color) # Bar
        draw.polygon([(w-p-5, h/2), (p, p), (p, h-p)], fill=color) # Triangle Right
        
    return ctk.CTkImage(img, size=size)
