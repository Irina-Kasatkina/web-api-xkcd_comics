import os
import random
import shutil
from pathlib import Path, PurePath
from urllib.parse import unquote, urlsplit

import requests
from dotenv import load_dotenv


TEMP_SUBDIR = 'images'
VK_API_VERSION = '5.131'


def check_vk_response(response):
    """ Проверяет правильность ответа от API vk.com. """

    response_payload = response.json()
    if 'response' in response_payload:
        return response_payload['response']

    raise requests.HTTPError(response_payload['error_msg'])


def download_comic_from_xkcd(comic_number: int, comics_dirpath: Path):
    """ Загружает комикс с заданным номером с сайта xkcd.com на диск. """

    response = requests.get(f'https://xkcd.com/{comic_number}/info.0.json')
    response.raise_for_status()

    response_payload = response.json()
    comic_image_url = response_payload['img']
    comic_message = response_payload['alt']

    response = requests.get(comic_image_url)
    response.raise_for_status()

    comic_image_url_path = urlsplit(comic_image_url).path
    comic_image_filename = unquote(PurePath(comic_image_url_path).name)
    comic_image_filepath = comics_dirpath / comic_image_filename

    with open(comic_image_filepath, 'wb') as comic_image_file:
        comic_image_file.write(response.content)

    return comic_message, comic_image_filepath


def get_vk_wall_upload_url(access_token: str) -> str:
    """ Получает c vk.com url для загрузки картинок. """

    method = 'photos.getWallUploadServer'
    url = f'https://api.vk.com/method/{method}'
    params = {
        'access_token': access_token,
        'v': VK_API_VERSION,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    return check_vk_response(response)['upload_url']


def post_comic_on_vk(access_token: str, group_id: str,
                     comic_message: str, comic_image_filepath: Path):
    """ Отправляет на vk комикс и публикует его на стене группы. """

    upload_url = get_vk_wall_upload_url(access_token)
    photo, server, upload_hash = upload_image_to_vk(upload_url, comic_image_filepath)
    owner_id, photo_id = save_image_on_vk(access_token, photo, server, upload_hash)
    publish_comic_on_vk_wall(access_token, group_id, owner_id, photo_id, comic_message)


def publish_comic_on_vk_wall(access_token: str, group_id: str, 
                             owner_id: int, photo_id: int, message: str):
    """ Публикует комикс из альбома группы vk на стене группы. """

    method = 'wall.post'
    url = f'https://api.vk.com/method/{method}'
    params = {
        'access_token': access_token,
        'v': VK_API_VERSION,
        'owner_id': f'-{group_id}',
        'from_group': 1,
        'attachments': f'photo{owner_id}_{photo_id}',
        'message': message,
    }

    response = requests.post(url, params=params)
    response.raise_for_status()


def save_image_on_vk(access_token: str, 
                     photo: str, server: int, upload_hash: str) -> tuple:
    """ Сохраняет в альбоме группы vk загруженную картинку комикса. """

    method = 'photos.saveWallPhoto'
    url = f'https://api.vk.com/method/{method}'
    params = {
        'access_token': access_token,
        'v': VK_API_VERSION,
        'photo': photo,
        'server': server,
        'hash': upload_hash,
    }

    response = requests.post(url, params=params)
    response.raise_for_status()

    response_payload = check_vk_response(response)
    owner_id = response_payload[0]['owner_id']
    photo_id = response_payload[0]['id']
    return owner_id, photo_id


def upload_image_to_vk(upload_url: str, image_filepath: Path) -> tuple:
    """ Загружает на vk.com картинку. """

    with open(image_filepath, 'rb') as image_file:
        files = {'photo': image_file}
        response = requests.post(upload_url, files=files)

    response.raise_for_status()
    response_payload = response.json()

    photo = response_payload['photo']
    server = response_payload['server']
    upload_hash = response_payload['hash']
    return photo, server, upload_hash


def main():
    load_dotenv()
    vk_access_token = os.environ['VK_ACCESS_TOKEN']
    vk_group_id = os.environ['VK_GROUP_ID']

    temp_dirpath = Path.cwd() / TEMP_SUBDIR
    temp_dirpath.mkdir(parents=True, exist_ok=True)

    exception = None
    try:
        response = requests.get('https://xkcd.com/info.0.json')
        response.raise_for_status()
        comics_amount = response.json()['num']

        random_comic_number = random.randint(1, comics_amount)
        comic_message, comic_image_filepath = (
            download_comic_from_xkcd(random_comic_number, temp_dirpath)
        )
        post_comic_on_vk(vk_access_token, vk_group_id,
                         comic_message, comic_image_filepath)
    except:
        raise
    finally:
        shutil.rmtree(temp_dirpath)


if __name__ == '__main__':
    main()
