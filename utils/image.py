"""Utils corresponding to processing images"""
import base64
import io

from PIL import Image

from utils.exceptions import InvalidImageInput


def choose_best_fit_size(input_size):
    # Calculate the maximum possible size based on the input size
    max_size = max(input_size)
    max_possible_size = min(((max_size - 1) // 64 + 1) * 64, 1024)

    # Generate a list of valid sizes that are multiples of 64
    valid_sizes = []
    for width in range(128, max_possible_size + 1, 64):
        for height in range(128, max_possible_size + 1, 64):
            if (896 >= height >= 512 >= width) or (896 >= width >= 512 >= height):
                valid_sizes.append((width, height))

    # If there are no valid sizes, raise an error
    if not valid_sizes:
        raise InvalidImageInput("Size of image is too small")

    # Among valid sizes, find the size with the best ratio match
    input_ratio = input_size[0] / input_size[1]
    best_fit_size = None
    best_fit_ratio_diff = float("inf")

    for size in valid_sizes[::-1]:
        size_ratio = size[0] / size[1]
        ratio_diff = abs(input_ratio - size_ratio)

        if ratio_diff < best_fit_ratio_diff:
            best_fit_size = size
            best_fit_ratio_diff = ratio_diff

    return best_fit_size


def crop_and_resize_image(image):
    width, height = image.size
    target_size = choose_best_fit_size((width, height))
    input_ratio = width / height
    target_ratio = target_size[0] / target_size[1]

    if input_ratio > target_ratio:
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        right = left + new_width
        image = image.crop((left, 0, right, height))
    else:
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        bottom = top + new_height
        image = image.crop((0, top, width, bottom))

    resized_image = image.resize(target_size)
    return resized_image


def image_to_bytes(image):
    byte_stream = io.BytesIO()
    image.save(byte_stream, format='PNG')
    byte_stream.seek(0)
    image_bytes = byte_stream.read()
    return image_bytes


def resize_image(image_str: str):
    image_bytes = base64.b64decode(image_str)
    image_stream = io.BytesIO(image_bytes)
    image = Image.open(image_stream)
    image_resized = crop_and_resize_image(image)
    image_resized_bytes = image_to_bytes(image_resized)
    return image_resized_bytes
