# Семантические признаки музыкальных треков

Разбор двух Spotify-плейлистов для content-based рекомендаций. В исходной таблице 100 позиций, после удаления трёх пересечений — 97 уникальных треков.

[Открыть ноутбук в Google Colab](https://colab.research.google.com/github/akiooooo/music-semantic-features/blob/main/music_analysis.ipynb)

## Задания

1. [Сбор датасета](music_analysis.ipynb#task-1)
2. [Формирование набора признаков](music_analysis.ipynb#task-2)
3. [Извлечение признаков](music_analysis.ipynb#task-3)
4. [Анализ данных](music_analysis.ipynb#task-4)
5. [Похожесть и эмбеддинги](music_analysis.ipynb#task-5)

## Данные

- [Daily Mix 6](https://open.spotify.com/playlist/37i9dQZF1E39FJtUzeh2UV?si=_zf3vFIMT5y3A2CdbfpPuA), первые 50 позиций
- [VILLIAN Radio](https://open.spotify.com/playlist/37i9dQZF1E4wwkchMkSBWv?si=leedN1noRZGw2fTD14AyZQ), первые 50 позиций

Сохранённый CSV используется как снимок: содержимое плейлистов со временем обновляется. Отдельной фильтрации по артистам и жанрам не было.

## Что считается

Через `librosa` извлекаются tempo, RMS, onset rate, спектральные характеристики, chroma и 13 MFCC. Модель `laion/clap-htsat-unfused` строит 512-мерные эмбеддинги и выбирает zero-shot метки genre, mood, context и atmosphere.

Похожесть считается двумя способами:

- cosine similarity по 21 стандартизованному low-level признаку
- cosine similarity по CLAP-эмбеддингам

CLAP дал больше совпадений семантических меток у ближайших соседей. Для genre получилось 0.784 против 0.608, для mood — 0.845 против 0.763, для context — 0.598 против 0.454.

При этом сами плейлисты разделяются слабо. Ближайший сосед был из того же источника в 0.467 случаев на обычных признаках и в 0.518 на CLAP. Silhouette score в обоих случаях близок к нулю.

## Файлы

- `music_analysis.ipynb` — выполненный ноутбук
- `collect_dataset.py` — сбор первых 50 позиций каждого плейлиста
- `data/spotify_playlist_tracks_raw.csv` — исходные 100 позиций
- `data/music_dataset.csv` — 97 уникальных треков
- `data/music_dataset_enriched.csv` — итоговая таблица с признаками
- `data/clap_embeddings.npy` — CLAP-эмбеддинги
- `results/figures/` — сохранённые графики

## Запуск на Windows

```powershell
py -m pip install -r requirements.txt
py -m jupyter notebook music_analysis.ipynb
```

Для повторного сбора текущего состояния плейлистов:

```powershell
py collect_dataset.py
```
