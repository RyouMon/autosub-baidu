"""
Defines autosub's main functionality.
"""

#!/usr/bin/env python

from __future__ import absolute_import, print_function, unicode_literals

import argparse
import audioop
import math
import multiprocessing
import os
import subprocess
import sys
import tempfile
import wave
from aip import AipSpeech

from progressbar import ProgressBar, Percentage, Bar, ETA

from autosubb.constants import LANGUAGE_CODES
from autosubb.formatters import FORMATTERS

DEFAULT_SUBTITLE_FORMAT = 'srt'
DEFAULT_CONCURRENCY = 1
DEFAULT_LANGUAGE = '1537'


def percentile(arr, percent):
    """
    Calculate the given percentile of arr.
    """
    arr = sorted(arr)
    index = (len(arr) - 1) * percent
    floor = math.floor(index)
    ceil = math.ceil(index)
    if floor == ceil:
        return arr[int(index)]
    low_value = arr[int(floor)] * (ceil - index)
    high_value = arr[int(ceil)] * (index - floor)
    return low_value + high_value


class WAVConverter(object):
    """
    Class for converting a region of an input audio or video file into a WAV audio file
    """

    def __init__(self, source_path, include_before=0.25, include_after=0.25):
        self.source_path = source_path
        self.include_before = include_before
        self.include_after = include_after

    def __call__(self, region):
        try:
            start, end = region
            start = max(0, start - self.include_before)
            end += self.include_after
            temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            command = ["ffmpeg", "-ss", str(start), "-t", str(end - start),
                       "-y", "-i", self.source_path,
                       "-loglevel", "error", temp.name]
            use_shell = True if os.name == "nt" else False
            subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)
            read_data = temp.read()
            temp.close()
            os.unlink(temp.name)
            return read_data

        except KeyboardInterrupt:
            return None


class SpeechRecognizer(object):
    """
    Class for performing speech-to-text for an input WAV file.
    """

    _client = None

    def __init__(self,  app_id, api_key, secret_key, dev_pid='1537', rate=16000, retries=3):
        self.app_id = app_id
        self.api_key = api_key
        self.secret_key = secret_key
        self.rate = rate
        self.dev_pid = dev_pid
        self.retries = retries if retries >= 0 else 0

    @property
    def client(self):
        if not self._client:
            self._client = AipSpeech(self.app_id, self.api_key, self.secret_key)
        return self._client

    def __call__(self, data):
        try:
            for _ in range(self.retries):
                response = self.client.asr(data, 'wav', self.rate, {'dev_pid': self.dev_pid})
                if response['err_no']:
                    continue
                return response['result'][0]
            raise Exception('SpeechRecognizer: %s, err_code: %d' % (response['err_msg'], response['err_no']))
        except KeyboardInterrupt:
            return None


def extract_audio(filename, channels=1, rate=16000):
    """
    Extract audio from an input file to a temporary WAV file.
    """
    temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    if not os.path.isfile(filename):
        print("The given file does not exist: {}".format(filename))
        raise Exception("Invalid filepath: {}".format(filename))
    command = ["ffmpeg", "-y", "-i", filename,
               "-ac", str(channels), "-ar", str(rate),
               "-loglevel", "error", temp.name]
    use_shell = True if os.name == "nt" else False
    subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)
    return temp.name, rate


def find_speech_regions(filename, frame_width=4096, min_region_size=0.5, max_region_size=6):
    """
    Perform voice activity detection on a given audio file.
    """
    reader = wave.open(filename)
    sample_width = reader.getsampwidth()
    rate = reader.getframerate()
    n_channels = reader.getnchannels()
    chunk_duration = float(frame_width) / rate

    n_chunks = int(math.ceil(reader.getnframes() * 1.0 / frame_width))
    energies = []

    for _ in range(n_chunks):
        chunk = reader.readframes(frame_width)
        energies.append(audioop.rms(chunk, sample_width * n_channels))

    threshold = percentile(energies, 0.2)

    elapsed_time = 0

    regions = []
    region_start = None

    for energy in energies:
        is_silence = energy <= threshold
        max_exceeded = region_start and elapsed_time - region_start >= max_region_size

        if (max_exceeded or is_silence) and region_start:
            if elapsed_time - region_start >= min_region_size:
                regions.append((region_start, elapsed_time))
                region_start = None

        elif (not region_start) and (not is_silence):
            region_start = elapsed_time
        elapsed_time += chunk_duration
    return regions


def generate_subtitles(source_path,
                       output=None,
                       concurrency=DEFAULT_CONCURRENCY,
                       subtitle_file_format=DEFAULT_SUBTITLE_FORMAT,
                       app_id=None,
                       api_key=None,
                       secret_key=None,
                       dev_pid=DEFAULT_LANGUAGE,
                       ):
    """
    Given an input audio/video file, generate subtitles in the specified language and format.
    """
    audio_filename, audio_rate = extract_audio(source_path)

    regions = find_speech_regions(audio_filename)

    pool = multiprocessing.Pool(concurrency)
    converter = WAVConverter(source_path=audio_filename)
    recognizer = SpeechRecognizer(app_id=app_id, api_key=api_key, secret_key=secret_key, dev_pid=dev_pid)

    transcripts = []
    if regions:
        try:
            widgets = ["Converting speech regions to WAV files: ", Percentage(), ' ', Bar(), ' ', ETA()]
            pbar = ProgressBar(widgets=widgets, maxval=len(regions)).start()
            extracted_regions = []
            for i, extracted_region in enumerate(pool.imap(converter, regions)):
                extracted_regions.append(extracted_region)
                pbar.update(i)
            pbar.finish()

            widgets = ["Performing speech recognition: ", Percentage(), ' ', Bar(), ' ', ETA()]
            pbar = ProgressBar(widgets=widgets, maxval=len(regions)).start()
            for i, transcript in enumerate(pool.imap(recognizer, extracted_regions)):
                transcripts.append(transcript)
                pbar.update(i)
            pbar.finish()

        except KeyboardInterrupt:
            pbar.finish()
            pool.terminate()
            pool.join()
            print("Cancelling transcription")
            raise

    timed_subtitles = [(r, t) for r, t in zip(regions, transcripts) if t]
    formatter = FORMATTERS.get(subtitle_file_format)
    formatted_subtitles = formatter(timed_subtitles)

    dest = output

    if not dest:
        base = os.path.splitext(source_path)[0]
        dest = "{base}.{format}".format(base=base, format=subtitle_file_format)

    with open(dest, 'wb') as output_file:
        output_file.write(formatted_subtitles.encode("utf-8"))

    os.remove(audio_filename)

    return dest


def validate(args):
    """
    Check that the CLI arguments passed to autosub are valid.
    """
    if args.format not in FORMATTERS:
        print(
            "Subtitle format not supported. "
            "Run with --list-formats to see all supported formats."
        )
        return False

    if args.lang not in LANGUAGE_CODES.keys():
        print(
            "Source language not supported. "
            "Run with --list-languages to see all supported languages."
        )
        return False

    if not args.source_path:
        print("Error: You need to specify a source path.")
        return False

    return True


def main():
    """
    Run autosub as a command-line program.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('source_path', help="Path to the video or audio file to subtitle",
                        nargs='?')
    parser.add_argument('-C', '--concurrency', help="Number of concurrent API requests to make",
                        type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument('-o', '--output',
                        help="Output path for subtitles (by default, subtitles are saved in \
                        the same directory and name as the source path)")
    parser.add_argument('-F', '--format', help="Destination subtitle format",
                        default=DEFAULT_SUBTITLE_FORMAT)
    parser.add_argument('-L', '--lang', help="Language spoken in source file",
                        default=DEFAULT_LANGUAGE)
    parser.add_argument('-K', '--api-key',
                        help="The Baidu Cloud API key to be used.")
    parser.add_argument('-S', '--secret-key',
                        help="The Baidu Cloud Secret Key to be used.")
    parser.add_argument('-A', '--app-id',
                        help="The Baidu Cloud AppID to be used.")
    parser.add_argument('--list-formats', help="List all available subtitle formats",
                        action='store_true')
    parser.add_argument('--list-languages', help="List all available source/destination languages",
                        action='store_true')

    args = parser.parse_args()

    if args.list_formats:
        print("List of formats:")
        for subtitle_format in FORMATTERS:
            print("{format}".format(format=subtitle_format))
        return 0

    if args.list_languages:
        print("List of all languages:")
        for code, language in sorted(LANGUAGE_CODES.items()):
            print("{code}\t{language}".format(code=code, language=language))
        return 0

    if not validate(args):
        return 1

    try:
        subtitle_file_path = generate_subtitles(
            source_path=args.source_path,
            concurrency=args.concurrency,
            subtitle_file_format=args.format,
            output=args.output,
            api_key=args.api_key,
            app_id=args.app_id,
            secret_key=args.secret_key,
            dev_pid=args.lang,
        )
        print("Subtitles file created at {}".format(subtitle_file_path))
    except KeyboardInterrupt:
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
