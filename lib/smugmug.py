# -*- coding: utf-8 -*-

import re, urllib, urllib2, urlparse, hashlib
import os.path, json, logging
import requests
from fs_utils import encode_path

API_VERSION='1.2.2'
API_URL='https://secure.smugmug.com/services/api/json/1.2.2/'
UPLOAD_URL='http://upload.smugmug.com/'

class SmugmugException(Exception):
    def __init__(self, response):
        self.response = response
        super(Exception, self).__init__()
    pass

class API(object):
    def __init__(self, api_key, id, password):
        self.session = None
        self.cookie = {}
        self.api_key = api_key
        self.id = id
        self.password = password

    def login(self):
        res = self._call("smugmug.login.withPassword",
                {"APIKey": self.api_key,
                 "EmailAddress": self.id,
                 "Password": self.password})
        self.session = res["Login"]["Session"]["id"]

    def change_album_setting(self, album_id, args={}):
        args = dict(args)
        args["AlbumID"] = album_id
        return self._call("smugmug.albums.changeSettings", args)

    def get_albums(self):
        return self._call("smugmug.albums.get")["Albums"]

    def get_images(self, album_id, album_key, args={}):
        args["AlbumID"] = album_id
        args["AlbumKey"] = album_key
        return self._call("smugmug.images.get", args)["Album"]["Images"]

    def get_exif(self, image_id, image_key):
        return self._call("smugmug.images.getEXIF",
                          {"ImageID": image_id, "ImageKey": image_key})

    def get_image_info(self, image_id, image_key):
        return self._call("smugmug.images.getInfo",
                          {"ImageID": image_id, "ImageKey": image_key})

    def delete_image(self, image_id):
        return self._call("smugmug.images.delete",
                          {"ImageID": image_id})
    def delete_album(self, album_id):
        return self._call("smugmug.albums.delete",
                          {"AlbumID": album_id})

    def change_image_setting(self, image_id, args={}):
        args = dict(args)
        args["ImageID"] = image_id
        return self._call("smugmug.images.changeSettings", args)

    def get_categories(self):
        cate = self._call("smugmug.categories.get")
        return dict((d["Name"], d["id"]) for d in cate["Categories"])

    def get_subcategories(self, category_id):
        try:
            cate = self._call("smugmug.subcategories.get",
                    {"CategoryID": category_id})
            return dict((d["Name"], d["id"]) for d in cate["SubCategories"])
        except SmugmugException as e:
            resp = e.response
            if isinstance(resp, dict) and resp["code"] == 15:
                return []
            raise

    def create_subcategory(self, category_id, name):
        logging.info("Creating subcategory %s ..", name)
        return self._call("smugmug.subcategories.create",
                {"CategoryID": category_id, "Name":
                    name})["SubCategory"]["id"]

    def create_album(self, name, category, options={}):
        options.update({"Title": name, "CategoryID": category})
        logging.debug("create_album %s", str(options))
        ret = self._call("smugmug.albums.create", options)["Album"]
        return (ret['Key'], ret['id'])

    def upload(self, path, album_id, length=None, md5=None, hidden=False, options={}):
        # path = encode_path(path)
        if length is None or md5 is None:
            contents = open(encode_path(path), 'rb').read()
            length = len(contents)
            md5 = hashlib.md5(contents).hexdigest()
        # args = {'Content-Length': length,
        #         'Content-MD5': md5,
        #         'X-Smug-SessionID': self.session,
        #         'X-Smug-Version': API_VERSION,
        #         'X-Smug-ResponseType': 'JSON',
        #         'X-Smug-AlbumID': album_id,
        #         'X-Smug-FileName': os.path.basename(path) }
        filename = os.path.basename(path)
        if any(ord(ch) >= 128 for ch in filename):
            ascii = filename.encode('ascii', 'ignore')
            name_portion = '.'.join(ascii.split('.')[:-1])
            ext = ascii.split('.')[-1]
            filename = '-'.join(['escaped', name_portion, md5[:10]]) + '.' + ext
            logging.info('Filename is not ASCII: replacing with md5 %s ..',
                         filename)
        args = {'Content-Length': length,
                'Content-MD5': md5,
                'X-Smug-SessionID': self.session,
                'X-Smug-Version': API_VERSION,
                'X-Smug-ResponseType': 'JSON',
                'X-Smug-AlbumID': album_id,
                'X-Smug-FileName': filename,
                # 'Content-Type': 'multipart/form-data'
               }
        args.update(options)
        if hidden:
            args['X-Smug-Hidden'] = 'true'
        ret = requests.post(UPLOAD_URL, headers=args, 
                            files={'file': (filename, open(encode_path(path), 'rb'))})
        ret.encoding = 'utf-8'
        print ret.text
        return ret.json()
        # request = urllib2.Request(UPLOAD_URL, data, args)
        # return self._http_request(request)

    def download(self, url, target):
        req = requests.get(url, cookies=self.cookie)
        with open(target, 'wb') as fp:
            for chunk in req.iter_content(1024*1024):
                fp.write(chunk)

    def _call(self, method, params={}):
        params = dict(params)
        if self.session and "SessionID" not in params:
            params["SessionID"] = self.session
        params['method'] = method

        ret = requests.get(API_URL, params=params, cookies=self.cookie)
        self.cookie.update(ret.cookies.get_dict())
        return ret.json()

    def _http_request(self, request):
        for it in xrange(5):
            try:
                response_obj = urllib2.urlopen(request)
                response = response_obj.read()
                result = json.loads(response)

                meta_info = response_obj.info()
                if meta_info.has_key("set-cookie"):
                    match = re.search('(_su=\S+);', meta_info["set-cookie"])
                    if match and match.group(1) != "_su=deleted":
                        self.su_cookie = match.group(1)
                if result["stat"] != "ok":
                    raise SmugmugException(result)
                return result
            except:
                raise
            # except SmugmugException as e:
            #     logging.error("SmugmugException: %s", str(e.response))
            #     raise
            # except Exception as e:
            #     logging.error("Exception during request: %s", str(e))
            #     continue
        logging.info("API request failed. Request was:\n%s\n"
                "Response was:\n%s", request.get_full_url(),
                str(response))
        raise SmugmugException(response)

if __name__ == "__main__":
    api = API('api key', 
              'email',
              'password')
    api.login()
    print api.get_albums()
