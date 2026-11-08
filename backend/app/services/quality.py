"""Cheap photo checks before running the models. Only the minimum size is a hard rule; blur is a warning because the
threshold is a starting value that should be tuned on real farmer photos."""
import numpy as np
from PIL import Image

MIN_SIDE_PX = 128          # smaller than this: cannot be assessed -> ask for another photo
SMALL_SIDE_PX = 224        # the model's input size; below it detail is lost
BLUR_THRESHOLD = 40.0      # variance of the Laplacian on a <=512 px grayscale copy; lower = blurrier (tune me)


class PhotoTooSmall(Exception):
    pass


def blur_score(image: Image.Image) -> float:
    g = image.convert("L")
    g.thumbnail((512, 512))
    a = np.asarray(g, dtype=np.float32)
    if min(a.shape) < 3:
        return 0.0
    lap = a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:] - 4 * a[1:-1, 1:-1]
    return float(lap.var())


def check(image: Image.Image) -> dict:
    w, h = image.size
    if min(w, h) < MIN_SIDE_PX:
        raise PhotoTooSmall(f"The photo is too small ({w}x{h}). Please take a closer photo of one leaf.")
    warnings = []
    if min(w, h) < SMALL_SIDE_PX:
        warnings.append("The photo is quite small, so the result may be less reliable. Try a closer photo.")
    score = blur_score(image)
    if score < BLUR_THRESHOLD:
        warnings.append("The photo looks blurry. Hold the phone steady, tap to focus on the leaf, and use good daylight.")
    return {"width": w, "height": h, "blur_score": round(score, 1), "warnings": warnings}
