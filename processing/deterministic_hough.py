"""Deterministic wrapper for OpenCV's probabilistic Hough transform."""

import threading

import cv2


_HOUGH_LOCK = threading.Lock()
_HOUGH_SEED = 20260828


def hough_lines_p(image, *, rho, theta, threshold, min_line_length, max_line_gap):
    """Run HoughLinesP without cross-request RNG/thread-state variation."""
    with _HOUGH_LOCK:
        previous_threads = cv2.getNumThreads()
        try:
            cv2.setNumThreads(1)
            cv2.setRNGSeed(_HOUGH_SEED)
            return cv2.HoughLinesP(
                image,
                rho=rho,
                theta=theta,
                threshold=threshold,
                minLineLength=min_line_length,
                maxLineGap=max_line_gap,
            )
        finally:
            cv2.setNumThreads(previous_threads)
