import os
from core.errors import StopCaptchaRetry


def solve_captcha(image_factory, solver_factory):
    solver = solver_factory()
    solver.on_begin()
    try:
        while True:
            captcha_image = image_factory()
            solver.on_new_image(captcha_image.image_data)
            while True:
                try:
                    answer = solver.request_input()
                except StopCaptchaRetry:
                    return None
                if answer is not None:
                    success = captcha_image.check_answer(answer)
                    if success:
                        return captcha_image
                    else:
                        solver.on_invalid_answer()
                else:
                    break
    finally:
        solver.on_end()


class ConsoleCaptchaSolver:
    def __init__(self, captcha_path):
        self.captcha_path = captcha_path

    @staticmethod
    def on_begin():
        print("Please input the captcha answer. You may enter 'change' to ")
        print("get a new captcha, or enter 'abort' to cancel the purchase.")

    def on_new_image(self, image_data):
        with open(self.captcha_path, "wb") as f:
            f.write(image_data)
        print("The captcha image has been saved at: " + os.path.abspath(self.captcha_path))

    @staticmethod
    def request_input():
        answer = input("Enter captcha answer: ")
        test_answer = answer.upper()
        if test_answer == "CHANGE":
            answer = None
        elif test_answer == "ABORT":
            raise StopCaptchaRetry()
        return answer

    @staticmethod
    def on_invalid_answer():
        print("Incorrect captcha answer! Please check your answer and ")
        print("try again, or type 'change' to get a new captcha image.")

    def on_end(self):
        os.remove(self.captcha_path)