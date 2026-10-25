import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests
from tqdm.auto import tqdm


ЖАНРЫ = {
    132: 'pop',
    116: 'rap/hip-hop',
    152: 'rock',
    113: 'dance',
    165: 'r&b',
    85: 'alternative',
    106: 'electro',
    466: 'folk',
    129: 'jazz',
    98: 'classical'
}


def запросить_json(адрес, попытки=3):
    for номер_попытки in range(попытки):
        ответ = requests.get(адрес, timeout=30)
        if ответ.ok:
            данные = ответ.json()
            if not данные.get('error'):
                return данные
        time.sleep(1 + номер_попытки)
    raise RuntimeError(f'не удалось получить данные: {адрес}')


def собрать_датасет(на_жанр=10, максимум_на_артиста=2):
    строки = []
    счетчик_артистов = {}
    собранные_id = set()

    for жанр_id, жанр in ЖАНРЫ.items():
        адрес = f'https://api.deezer.com/chart/{жанр_id}/tracks?limit=50'
        кандидаты = запросить_json(адрес)['data']
        добавлено = 0

        for трек in кандидаты:
            исполнитель = трек['artist']['name']
            if трек['id'] in собранные_id:
                continue
            if счетчик_артистов.get(исполнитель, 0) >= максимум_на_артиста:
                continue
            if not трек.get('preview'):
                continue

            подробно = запросить_json(f"https://api.deezer.com/track/{трек['id']}")
            строки.append({
                'track_id': подробно['id'],
                'название': подробно['title'],
                'исполнитель': подробно['artist']['name'],
                'альбом': подробно['album']['title'],
                'жанр': жанр,
                'длительность_сек': подробно['duration'],
                'дата_релиза': подробно.get('release_date'),
                'рейтинг_deezer': подробно.get('rank'),
                'explicit': подробно.get('explicit_lyrics'),
                'track_url': подробно['link'],
                'preview_url': подробно['preview'],
                'источник': 'Deezer API'
            })
            собранные_id.add(трек['id'])
            счетчик_артистов[исполнитель] = счетчик_артистов.get(исполнитель, 0) + 1
            добавлено += 1
            time.sleep(0.05)

            if добавлено == на_жанр:
                break

        if добавлено < на_жанр:
            raise RuntimeError(f'для жанра {жанр} собрано только {добавлено} треков')

    датасет = pd.DataFrame(строки).drop_duplicates('track_id').reset_index(drop=True)
    return датасет


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download-previews', action='store_true')
    аргументы = parser.parse_args()

    папка_данных = Path('data')
    папка_данных.mkdir(exist_ok=True)
    датасет = собрать_датасет()
    датасет.to_csv(папка_данных / 'music_dataset.csv', index=False, encoding='utf-8-sig')

    if аргументы.download_previews:
        папка_аудио = папка_данных / 'audio'
        папка_аудио.mkdir(exist_ok=True)
        for строка in tqdm(датасет.itertuples(), total=len(датасет), desc='аудиофрагменты'):
            путь = папка_аудио / f'{строка.track_id}.mp3'
            if not путь.exists():
                путь.write_bytes(requests.get(строка.preview_url, timeout=60).content)

    статистика = {
        'треков': int(len(датасет)),
        'исполнителей': int(датасет['исполнитель'].nunique()),
        'жанров': int(датасет['жанр'].nunique()),
        'максимум_треков_одного_исполнителя': int(датасет['исполнитель'].value_counts().max()),
        'треков_по_жанрам': датасет['жанр'].value_counts().sort_index().to_dict()
    }
    (папка_данных / 'dataset_stats.json').write_text(
        json.dumps(статистика, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(f"tracks: {статистика['треков']}")
    print(f"artists: {статистика['исполнителей']}")
    print(f"genres: {статистика['жанров']}")


if __name__ == '__main__':
    main()
