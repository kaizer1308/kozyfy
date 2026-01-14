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
    elif name == "lyrics":
        # Draw a microphone/lyrics icon - stylized text lines
        line_color = color
        # Three horizontal lines representing lyrics text
        line_height = 2
        line_gap = 4
        start_y = h // 4
        
        # Line 1 (longer)
        draw.rectangle([(p + 2, start_y), (w - p - 2, start_y + line_height)], fill=line_color)
        # Line 2 (medium)
        draw.rectangle([(p + 4, start_y + line_gap + line_height), (w - p - 4, start_y + line_gap + 2*line_height)], fill=line_color)
        # Line 3 (shorter)
        draw.rectangle([(p + 6, start_y + 2*line_gap + 2*line_height), (w - p - 6, start_y + 2*line_gap + 3*line_height)], fill=line_color)
        # Music note accent
        draw.ellipse([(w - p - 6, h - p - 4), (w - p - 2, h - p)], fill=line_color)
        
    return ctk.CTkImage(img, size=size)
