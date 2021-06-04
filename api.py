import json
import time
import os
import stat
import sys
import shutil
import requests
import zipfile
import subprocess
import pathlib
import tempfile
import random

API_URL = 'https://api.gologin.app'


class GoLogin(object):
    def __init__(self, options):
        self.access_token = options.get('token')

        self.tmpdir = options.get('tmpdir', tempfile.gettempdir())
        self.address = options.get('address', '127.0.0.1')
        self.extra_params = options.get('extra_params', [])
        self.port = options.get('port', random.randrange(2000, 40000))
        home = str(pathlib.Path.home())
        self.executablePath = options.get('executablePath',
                                          os.path.join(home, '.gologin/browser/orbita-browser/chrome'))
        self.set_profile_id(options.get('profile_id'))

    def set_profile_id(self, profile_id):
        self.profile_id = profile_id
        if self.profile_id is None:
            return
        self.profile_path = os.path.join(self.tmpdir, 'gologin_' + self.profile_id)
        self.profile_zip_path = os.path.join(self.tmpdir, 'gologin_' + self.profile_id + '.zip')
        self.profile_zip_path_upload = os.path.join(self.tmpdir, 'gologin_' + self.profile_id + '_upload.zip')

    def spawn_browser(self):
        proxy = self.proxy
        proxy_host = ''
        if proxy:
            proxy_host = proxy.get('host')
            proxy = f'{proxy["mode"]}://{proxy["host"]}:{proxy["port"]}'

        tz = self.tz.get('timezone')

        params = [
            self.executablePath,
            '--remote-debugging-port=' + str(self.port),
            '--user-data-dir=' + self.profile_path,
            '--password-store=basic',
            '--tz=' + tz,
            '--gologin-profile=' + self.profile_name,
            '--lang=en',
        ]
        if proxy:
            hr_rules = '"MAP * 0.0.0.0 , EXCLUDE %s"' % proxy_host
            params.append('--proxy-server=' + proxy)
            params.append('--host-resolver-rules=' + hr_rules)

        for param in self.extra_params:
            params.append(param)

        if sys.platform == "darwin":
            subprocess.Popen(params)
        else:
            subprocess.Popen(params, start_new_session=True)

        try_count = 1
        url = str(self.address) + ':' + str(self.port)
        while try_count < 100:
            try:
                data = requests.get('http://' + url + '/json').content
                break
            except:
                try_count += 1
                time.sleep(1)

        return url

    def start(self):
        self.create_startup()
        return self.spawn_browser()

    def zipdir(self, path, ziph):
        for root, dirs, files in os.walk(path):
            for file in files:
                path = os.path.join(root, file)
                if not os.path.exists(path):
                    continue
                if stat.S_ISSOCK(os.stat(path).st_mode):
                    continue
                ziph.write(path, path.replace(self.profile_path, ''))

    def stop(self):
        self.sanitize_profile()
        self.commit_profile()
        os.remove(self.profile_zip_path_upload)
        shutil.rmtree(self.profile_path)

    def commit_profile(self):
        zipf = zipfile.ZipFile(self.profile_zip_path_upload, 'w', zipfile.ZIP_DEFLATED)
        self.zipdir(self.profile_path, zipf)
        zipf.close()

        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'User-Agent': 'Selenium-API'
        }
        print('profile size=', os.stat(self.profile_zip_path_upload).st_size)

        signedUrl = requests.get(API_URL + '/browser/' + self.profile_id + '/storage-signature',
                                 headers=headers).content.decode('utf-8')

        requests.put(signedUrl, data=open(self.profile_zip_path_upload, 'rb'))

        print('commit profile complete')

    def sanitize_profile(self):
        remove_dirs = [
            'Default/Cache',
            'biahpgbdmdkfgndcmfiipgcebobojjkp',
            'afalakplffnnnlkncjhbmahjfjhmlkal',
            'cffkpbalmllkdoenhmdmpbkajipdjfam',
            'Dictionaries',
            'enkheaiicpeffbfgjiklngbpkilnbkoi',
            'oofiananboodjbbmdelgdommihjbkfag',
            'SingletonCookie',
            'SingletonLock',
            'SingletonSocket',
            'SafetyTips',
            'Default/Service Worker/CacheStorage',
            'Default/Code Cache',
            'Default/.org.chromium.Chromium.*'
        ]

        for d in remove_dirs:
            fpath = os.path.join(self.profile_path, d)
            if os.path.exists(fpath):
                try:
                    shutil.rmtree(fpath)
                except:
                    continue

    def get_time_zone(self):
        # proxy = self.proxy
        # if proxy:
        #     proxies = {proxy.get('mode'): f'{proxy["mode"]}://{proxy["host"]}:{proxy["port"]}'}
        #     data = requests.get('https://time.gologin.app', proxies=proxies)
        # else:
        #     data = requests.get('https://time.gologin.app')
        # return json.loads(data.content.decode('utf-8'))
        return {  # TODO maybe fix
            "ip": "207.154.198.134",
            "timezone": "Europe/Berlin",
            "accuracy": 100,
            "ll": [
                "50.11090",
                "8.68213"
            ],
            "country": "DE"
        }

    def get_profile(self, profile_id=None):
        profile = self.profile_id if profile_id is None else profile_id
        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'User-Agent': 'Selenium-API'
        }
        return json.loads(requests.get(API_URL + '/browser/' + profile, headers=headers).content.decode('utf-8'))

    def download_profile_zip(self):
        s3path = self.profile.get('s3Path', '')
        if s3path == '':
            # print('downloading profile direct')
            headers = {
                'Authorization': 'Bearer ' + self.access_token,
                'User-Agent': 'Selenium-API'
            }
            data = requests.get(API_URL + '/browser/' + self.profile_id, headers=headers).content
        else:
            # print('downloading profile s3')
            s3url = 'https://s3.eu-central-1.amazonaws.com/gprofiles.gologin/' + s3path.replace(' ', '+');
            data = requests.get(s3url).content

        if len(data) == 0:
            self.create_startup()
        else:
            with open(self.profile_zip_path, 'wb') as f:
                f.write(data)

        try:
            self.extract_profile_zip()
        except:
            self.create_empty_profile()
            self.extract_profile_zip()

        if not os.path.exists(os.path.join(self.profile_path, 'Default/Preferences')):
            self.create_empty_profile()
            self.extract_profile_zip()

    def create_empty_profile(self):
        print('createEmptyProfile')
        empty_profile = '../gologin_zeroprofile.zip'
        if not os.path.exists(empty_profile):
            empty_profile = 'gologin_zeroprofile.zip'
        shutil.copy(empty_profile, self.profile_zip_path)

    def extract_profile_zip(self):
        with zipfile.ZipFile(self.profile_zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.profile_path)
        os.remove(self.profile_zip_path)

    def get_geolocation_params(self, profileGeolocationParams, tzGeolocationParams):
        if profileGeolocationParams.get('fillBasedOnIp'):
            return {
                'mode': profileGeolocationParams['mode'],
                'latitude': float(tzGeolocationParams['latitude']),
                'longitude': float(tzGeolocationParams['longitude']),
                'accuracy': float(tzGeolocationParams['accuracy']),
            }

        return {
            'mode': profileGeolocationParams['mode'],
            'latitude': profileGeolocationParams['latitude'],
            'longitude': profileGeolocationParams['longitude'],
            'accuracy': profileGeolocationParams['accuracy'],
        }

    def convert_preferences(self, preferences):
        resolution = preferences.get('resolution', '1920x1080')
        preferences['screenWidth'] = int(resolution.split('x')[0])
        preferences['screenHeight'] = int(resolution.split('x')[1])

        self.tz = self.get_time_zone()
        # print('tz=', self.tz)
        tzGeoLocation = {
            'latitude': self.tz['ll'][0],
            'longitude': self.tz['ll'][1],
            'accuracy': self.tz['accuracy'],
        }

        preferences['geoLocation'] = self.get_geolocation_params(preferences['geolocation'], tzGeoLocation)

        preferences['webRtc'] = {
            'mode': 'public' if preferences.get('webRTC', {}).get('mode') == 'alerted' else preferences.get('webRTC',
                                                                                                            {}).get(
                'mode'),
            'publicIP': self.tz['ip'] if preferences.get('webRTC', {}).get('fillBasedOnIp') else preferences.get(
                'webRTC', {}).get('publicIp'),
            'localIps': preferences.get('webRTC', {}).get('localIps', [])
        }

        preferences['timezone'] = {
            'id': self.tz.get('timezone')
        }

        preferences['webgl_noise_value'] = preferences.get('webGL', {}).get('noise')
        preferences['get_client_rects_noise'] = preferences.get('webGL', {}).get('getClientRectsNoise')
        preferences['canvasMode'] = preferences.get('canvas', {}).get('mode')
        preferences['canvasNoise'] = preferences.get('canvas', {}).get('noise')
        preferences['audioContext'] = {
            'enable': preferences.get('audioContext').get('mode', 'off'),
            'noiseValue': preferences.get('audioContext').get('noise'),
        }

        preferences['webgl'] = {
            'metadata': {
                'vendor': preferences.get('webGLMetadata', {}).get('vendor'),
                'renderer': preferences.get('webGLMetadata', {}).get('renderer'),
                'enabled': preferences.get('webGLMetadata', {}).get('mode') == 'mask',
            }
        }

        if preferences.get('navigator', {}).get('userAgent'):
            preferences['userAgent'] = preferences.get('navigator', {}).get('userAgent')

        if preferences.get('navigator', {}).get('doNotTrack'):
            preferences['doNotTrack'] = preferences.get('navigator', {}).get('doNotTrack')

        if preferences.get('navigator', {}).get('hardwareConcurrency'):
            preferences['hardwareConcurrency'] = preferences.get('navigator', {}).get('hardwareConcurrency')

        if preferences.get('navigator', {}).get('language'):
            preferences['language'] = preferences.get('navigator', {}).get('language')

        return preferences

    def update_preferences(self):
        pref_file = os.path.join(self.profile_path, 'Default/Preferences')
        pfile = open(pref_file, 'r')
        preferences = json.load(pfile)
        pfile.close()
        profile = self.profile
        proxy = self.profile.get('proxy')
        if proxy and proxy.get('mode') == 'gologin':
            autoProxyServer = profile.get('autoProxyServer')
            splittedAutoProxyServer = autoProxyServer.split('://')
            splittedProxyAddress = splittedAutoProxyServer[1].split(':')
            port = splittedProxyAddress[1]

            proxy = {
                'mode': 'http',
                'host': splittedProxyAddress[0],
                'port': port,
                'username': profile.get('autoProxyUsername'),
                'password': profile.get('autoProxyPassword'),
                'timezone': profile.get('autoProxyTimezone', 'us'),
            }

            profile['proxy']['username'] = profile.get('autoProxyUsername')
            profile['proxy']['password'] = profile.get('autoProxyPassword')

        if not proxy or proxy.get('mode') == 'none':
            print('no proxy')
            proxy = None

        self.proxy = proxy
        self.profile_name = profile.get('name')
        if self.profile_name is None:
            print('empty profile name')
            print('profile=', profile)
            exit()

        gologin = self.convert_preferences(profile)
        preferences['gologin'] = gologin
        pfile = open(pref_file, 'w')
        json.dump(preferences, pfile)

    def create_startup(self):
        if os.path.exists(self.profile_path):
            shutil.rmtree(self.profile_path)
        self.profile = self.get_profile()
        self.download_profile_zip()
        self.update_preferences()

    def headers(self):
        return {
            'Authorization': 'Bearer ' + self.access_token,
            'User-Agent': 'Selenium-API'
        }

    def get_random_fingerprint(self, options=None):
        if options is None:
            options = {}

        os_type = options.get('os', 'win')
        return json.loads(
            requests.get(API_URL + '/browser/fingerprint?os=' + os_type, headers=self.headers()).content.decode(
                'utf-8'))

    def profiles(self):
        return json.loads(requests.get(API_URL + '/browser/', headers=self.headers()).content.decode('utf-8'))

    def create(self, options=None):
        profile_options = self.get_random_fingerprint()
        profile = {
            "name": options.get("name", 'None'),
            "notes": "",
            "browserType": "chrome",
            "os": options.get("os", 'win'),
            "startUrl": "google.com",
            "googleServicesEnabled": True,
            "lockEnabled": False,
            "audioContext": {
                "mode": "noise"
            },
            "canvas": {
                "mode": "noise"
            },
            "webRTC": {
                "mode": "disabled",
                "enabled": False,
                "customize": True,
                "fillBasedOnIp": True
            },
            'webGLMetadata': {
                "vendor": profile_options['webGLMetadata']['vendor'],
                "renderer": profile_options['webGLMetadata']['renderer']
            },
            "navigator": profile_options["navigator"],
            "proxyEnabled": True,
            "proxy": {
                "mode": options.get("proxy_mode"),
                "host": options.get("proxy_host"),
                "port": options.get("proxy_port"),
                "username": options.get("proxy_username"),
                "password": options.get("proxy_password"),
            },
            "profile": json.dumps(profile_options),
        }

        for _ in range(5):
            response = json.loads(
                requests.post(API_URL + '/browser/', headers=self.headers(), json=profile).content.decode('utf-8'))
            id = response.get('id')
            if id:
                return id
            time.sleep(2)
        else:
            raise Exception("Failed to create profile")

    def delete(self, profile_id=None):
        profile = self.profile_id if profile_id is None else profile_id
        requests.delete(API_URL + '/browser/' + profile, headers=self.headers())

    def update(self, options):
        profile = self.get_profile()
        for k, v in options.items():
            profile[k] = v
        return json.loads(
            requests.put(API_URL + '/browser/' + self.profile_id, headers=self.headers(), json=profile).content.decode(
                'utf-8'))
