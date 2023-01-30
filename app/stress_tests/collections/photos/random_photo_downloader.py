from urllib.request import urlretrieve

PHOTO_LIBRARY = "https://picsum.photos"


def download_photos(photo_number: int, photo_size: int) -> None:
    for i in range(photo_number):
        name = f"sample_photo_{i + 1}.jpg"
        urlretrieve(
            url=f"{PHOTO_LIBRARY}/{photo_size}",
            filename=name,
        )
        print("downloaded: ", name)


if __name__ == "__main__":
    number = 50
    size = 500
    download_photos(number, size)
