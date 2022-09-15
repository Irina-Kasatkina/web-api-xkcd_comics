import os
from pathlib import Path, PurePath
import random
import shutil
from urllib.parse import unquote, urlsplit

from dotenv import load_dotenv
import requests


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

    response_payload = get_comic_info_from_xkcd(comic_number)
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


def get_comic_info_from_xkcd(comic_number: int) -> dict:
    """ Получает с сайта xkcd.com информацию о комиксе с заданным номером. """

    response = requests.get(f'https://xkcd.com/{comic_number}/info.0.json')
    response.raise_for_status()
    return response.json()


def get_comics_amount():
    """ Получает c xkcd.com общее количество имеющихся комиксов. """

    response = requests.get('https://xkcd.com/info.0.json')
    response.raise_for_status()

    return response.json()['num']


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

    upload_response_payload = upload_image_to_vk(
        upload_url,
        comic_image_filepath
    )

    save_response_payload = save_image_on_vk(
        access_token,
        upload_response_payload
    )

    publish_comic_on_vk_wall(
        access_token,
        group_id,
        save_response_payload,
        comic_message
    )


def publish_comic_on_vk_wall(access_token: str,
                             group_id: str,
                             save_response_payload: dict,
                             message: str):
    """ Публикует комикс из альбома группы vk на стене группы. """

    method = 'wall.post'
    url = f'https://api.vk.com/method/{method}'
    params = {
        'access_token': access_token,
        'v': VK_API_VERSION,
        'owner_id': f'-{group_id}',
        'from_group': 1,
        'attachments': f'photo{save_response_payload[0]["owner_id"]}_'
                       f'{save_response_payload[0]["id"]}',
        'message': message,
    }

    response = requests.post(url, params=params)
    response.raise_for_status()


def save_image_on_vk(access_token: str, upload_response_payload: dict) -> dict:
    """ Сохраняет в альбоме группы vk загруженную картинку комикса. """

    method = 'photos.saveWallPhoto'
    url = f'https://api.vk.com/method/{method}'
    params = {
        'access_token': access_token,
        'v': VK_API_VERSION,
    }
    params.update(upload_response_payload)

    response = requests.post(url, params=params)
    response.raise_for_status()

    return check_vk_response(response)


def upload_image_to_vk(upload_url: str, image_filepath: Path) -> dict:
    """ Загружает на vk.com картинку. """

    with open(image_filepath, 'rb') as image_file:
        files = {'photo': image_file}
        response = requests.post(upload_url, files=files)

    response.raise_for_status()
    return response.json()


def main():
    load_dotenv()
    vk_access_token = os.environ['VK_ACCESS_TOKEN']
    vk_group_id = os.environ['VK_GROUP_ID']

    temp_dirpath = Path.cwd() / TEMP_SUBDIR
    temp_dirpath.mkdir(parents=True, exist_ok=True)

    exception = None
    try:
        comics_amount = get_comics_amount()
        random_comic_number = random.randint(1, comics_amount)
        comic_message, comic_image_filepath = (
            download_comic_from_xkcd(random_comic_number, temp_dirpath)
        )
        post_comic_on_vk(vk_access_token, vk_group_id,
                         comic_message, comic_image_filepath)
    except Exception as ex:
        exception = ex
    finally:
        shutil.rmtree(temp_dirpath)
        if exception:
            raise exception


if __name__ == '__main__':
    main()
