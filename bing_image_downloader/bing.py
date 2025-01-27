from pathlib import Path
import urllib.request
import urllib
import imghdr
import posixpath
import re
from PIL import Image
from io import BytesIO
import io
import json


"""
Python api to download image form Bing.
Author: Guru Prasad (g.gaurav541@gmail.com)
"""


def image_to_byte_array(image: Image) -> bytes:
    imgByteArr = io.BytesIO()
    image.save(imgByteArr, format="PNG")
    imgByteArr = imgByteArr.getvalue()
    return imgByteArr


def resize(url, size: tuple):

    response = urllib.request.urlopen(url)
    img = Image.open(BytesIO(response.read()))
    img = img.resize(size=size, resample=Image.LANCZOS)
    # kl=image_to_byte_array(img)
    # with open('pn.png','wb') as f:
    #     f.write(kl)
    return img


class Bing:
    def __init__(
        self,
        query,
        limit,
        output_dir,
        adult,
        timeout,
        filter="",
        resize=None,
        verbose=True,
        query_metadata=None,
    ):
        self.download_count = 0
        self.query = query
        self.output_dir = output_dir
        self.adult = adult
        self.filter = filter
        self.verbose = verbose
        self.seen = set()
        self.image_metadata = []  # Store metadata for downloaded images
        self.query_metadata = (
            query_metadata or {}
        )  # Store query metadata (country, theme)

        assert type(limit) == int, "limit must be integer"
        self.limit = limit
        assert type(timeout) == int, "timeout must be integer"
        self.timeout = timeout
        assert (type(resize) == tuple) or (
            resize is None
        ), "resize must be a tuple(height,width)"
        self.resize = resize

        # self.headers = {'User-Agent': 'Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}
        self.page_counter = 0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.11 (KHTML, like Gecko) "
            "Chrome/23.0.1271.64 Safari/537.11",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
            "Accept-Encoding": "none",
            "Accept-Language": "en-US,en;q=0.8",
            "Connection": "keep-alive",
        }

        # self.headers = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        # }

    def get_filter(self, shorthand):
        if shorthand == "line" or shorthand == "linedrawing":
            return "+filterui:photo-linedrawing"
        elif shorthand == "photo":
            return "+filterui:photo-photo"
        elif shorthand == "clipart":
            return "+filterui:photo-clipart"
        elif shorthand == "gif" or shorthand == "animatedgif":
            return "+filterui:photo-animatedgif"
        elif shorthand == "transparent":
            return "+filterui:photo-transparent"
        else:
            return ""

    def save_image(self, link, image_counter: int, metadata: dict = None):
        """Save image and metadata using the structure: country/theme/[images|metadata]/"""
        try:
            # Get country and theme from query metadata
            country = metadata.get("country", "unknown")
            theme = metadata.get("theme", "unknown")

            # Create directory structure
            country_dir = Path(self.output_dir) / country
            theme_dir = country_dir / theme
            images_dir = theme_dir / "images"
            metadata_dir = theme_dir / "metadata"

            # Create directories
            images_dir.mkdir(parents=True, exist_ok=True)
            metadata_dir.mkdir(parents=True, exist_ok=True)

            # Determine file type
            # file_type = "jpg"  # Default to jpg
            img_name = posixpath.basename(link)
            # if link.lower().endswith((".png", ".gif", ".bmp", ".webp")):

            #     file_type = link.split(".")[-1].lower()

            # Save image
            image_path = images_dir / f"img_{img_name}"

            if not self.resize:
                request = urllib.request.Request(link, None, self.headers)
                image = urllib.request.urlopen(request, timeout=self.timeout).read()
                if not imghdr.what(None, image):
                    raise ValueError("Invalid image, not saving {}\n".format(link))
                with open(str(image_path), "wb") as f:
                    f.write(image)
            else:
                img = resize(link, size=self.resize)
                image = image_to_byte_array(img)
                with open(str(image_path), "wb") as f:
                    f.write(image)

            # Save metadata
            if metadata:
                metadata["local_path"] = str(image_path)

                metadata_filename = img_name.split(".")[0] + "_metadata.json"
                metadata_path = metadata_dir / metadata_filename
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

            return str(image_path)

        except Exception as e:
            print(f"[!] Error saving image: {e}")
            raise e

    def download_image(self, link, metadata=None):
        self.download_count += 1
        try:
            if self.verbose:
                print(
                    "[%] Downloading Image #{} from {}".format(
                        self.download_count, link
                    )
                )

            image_path = self.save_image(link, self.download_count, metadata)
            if metadata:
                self.image_metadata.append(metadata)

            if self.verbose:
                print("[%] File Downloaded !\n")

        except Exception as e:
            self.download_count -= 1
            print("[!] Issue getting: {}\n[!] Error:: {}".format(link, e))

    def run(self):
        while (
            self.download_count < self.limit and self.page_counter < 50
        ):  # 50 pages max
            # if self.verbose:
            #     print("\n\n[!!]Indexing page: {}\n".format(self.page_counter + 1))
            # Parse the page source and download pics
            request_url = (
                "https://www.bing.com/images/search?q="
                + urllib.parse.quote_plus(self.query)
                + "&first="
                + str(self.page_counter)
                + "&count="
                + str(self.limit)
                + "&adlt="
                + self.adult
                + "&qft="
                + ("" if self.filter is None else self.get_filter(self.filter))
            )

            request = urllib.request.Request(request_url, None, headers=self.headers)
            response = urllib.request.urlopen(request)
            html = response.read().decode("utf8")
            if html == "":
                print("[%] No more images are available")
                break
            # Extract metadata
            links = re.findall("murl&quot;:&quot;(.*?)&quot;", html)
            source_links = re.findall("purl&quot;:&quot;(.*?)&quot;", html)
            titles = re.findall("t&quot;:&quot;(.*?)&quot;", html)
            source_titles = re.findall("pt&quot;:&quot;(.*?)&quot;", html)
            dimensions = re.findall("&quot;w&quot;:(\d+),&quot;h&quot;:(\d+)", html)

            links = [link.replace(" ", "%20") for link in links]

            # if len(links) == 0:
            #     print("[%] No images were found for query: {}".format(self.query))
            #     print("html: ", html)
            #     print("request_url: ", request_url)

            #     break
            if self.verbose:
                print(
                    "[%] Indexed {} Images on Page {}.".format(
                        len(links), self.page_counter + 1
                    )
                )

                print("\n===============================================\n")

            for idx, link in enumerate(links):
                if self.download_count < self.limit and link not in self.seen:
                    self.seen.add(link)
                    metadata = {
                        "image_url": link,
                        "source_url": (
                            source_links[idx] if idx < len(source_links) else None
                        ),
                        "title": titles[idx] if idx < len(titles) else None,
                        "source_title": (
                            source_titles[idx] if idx < len(source_titles) else None
                        ),
                        "width": (
                            int(dimensions[idx][0]) if idx < len(dimensions) else None
                        ),
                        "height": (
                            int(dimensions[idx][1]) if idx < len(dimensions) else None
                        ),
                        "country": self.query_metadata.get("country", "unknown"),
                        "theme": self.query_metadata.get("theme", "unknown"),
                        "query": self.query,
                    }
                    self.download_image(link, metadata)

            self.page_counter += 1
        print("\n\n[%] Done. Downloaded {} images.".format(self.download_count))
        return self.image_metadata
