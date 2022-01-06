# Autosub-baidu
  
### Auto-generated subtitles for any video

[Autosub](https://github.com/agermanidis/autosub) 是用于自动语音识别和字幕生成的实用程序。

但是这个项目已经不再维护了，而且在中国使用有些困难。
于是我克隆了这个项目的代码，在内部把Google Web Speech API替换为了[百度短语音识别API](https://ai.baidu.com/tech/speech/asr) 。

项目结构也做出了一些修改，使其即可以在命令行使用，也可以在其他代码中导入使用（主要目的是方便在代码中使用）。语言也改为了仅支持中文。

运行参数有些不一样，要想顺利使用这个新项目你必须提供`API_KEY`、`SECRET_KEY`和`APP_ID`。这里贴出了一些链接，可以跟随这些链接去自行探索：
1. [短语音识别标准版产品首页](https://ai.baidu.com/tech/speech/asr)
2. [百度AI开放平台语音技术新手入门](https://ai.baidu.com/ai-doc/SPEECH/qknh9i8ed) （通过阅读可以了解如何获得`API_KEY`、`SECRET_KEY`和`APP_ID`）

---

[Autosub](https://github.com/agermanidis/autosub) is a utility for automatic speech recognition and subtitle generation.

But this project is no longer maintained, and it is somewhat difficult to use in China.
So I cloned the code of this project and replaced Google Web Speech API with Baidu Short Speech Recognition API internally.

Now Autosub-baidu only supports Chinese.

### 安装 Installation

1. 安装 [ffmpeg](https://www.ffmpeg.org/).
2. 运行 `pip install autosub-baidu`.

### 用法 Usage

#### 从命令行使用（command line）：
```
python -m autosubb -h
usage: __main__.py [-h] [-C CONCURRENCY] [-o OUTPUT] [-F FORMAT] [-L LANG] [-K API_KEY] [-S SECRET_KEY] [-A APP_ID]
                   [--list-formats] [--list-languages]
                   [source_path]

positional arguments:
  source_path           Path to the video or audio file to subtitle

optional arguments:
  -h, --help            show this help message and exit
  -C CONCURRENCY, --concurrency CONCURRENCY
                        Number of concurrent API requests to make
  -o OUTPUT, --output OUTPUT
                        Output path for subtitles (by default, subtitles are saved in the same directory and name as
                        the source path)
  -F FORMAT, --format FORMAT
                        Destination subtitle format
  -L LANG, --lang LANG  Language spoken in source file. default 1537.
  -K API_KEY, --api-key API_KEY
                        The Baidu Cloud API key to be used.
  -S SECRET_KEY, --secret-key SECRET_KEY
                        The Baidu Cloud Secret Key to be used.
  -A APP_ID, --app-id APP_ID
                        The Baidu Cloud AppID to be used.
  --list-formats        List all available subtitle formats
  --list-languages      List all available source/destination languages
```

#### 从代码使用:
```py
import sys

from autosubb import generate_subtitles

APP_ID = '2*****0'
API_KEY = 'W********************o'
SECRET_KEY = 'X******************************5'

filename = 'audio.mp3'


def main():
    subtitles = generate_subtitles(
        source_path=filename,
        app_id=APP_ID,
        api_key=API_KEY,
        secret_key=SECRET_KEY,
        concurrency=2,
        dev_pid='80001',
    )
    print(subtitles)


if __name__ == '__main__':
    sys.exit(main())
```

```py
[((2.3040000000000003, 4.608000000000002), '从前有一对仙人夫妻。'),
 ((5.376000000000003, 7.424000000000005), '他们常常到山顶上下棋。'),
...
 ((56.83200000000004, 59.392000000000046), '猴子的眼睛一直盯着这盘水蜜桃。'),
 ((60.41600000000005, 63.48800000000005), '战胜对手，其实就是战胜对手的弱点。')]
```

### License

MIT
