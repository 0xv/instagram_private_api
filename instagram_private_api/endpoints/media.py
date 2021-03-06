import json
import re

from ..utils import gen_user_breadcrumb
from ..compatpatch import ClientCompatPatch


class MediaEndpointsMixin(object):

    def media_info(self, media_id):
        """
        Get media info

        :param media_id:
        :return:
        """
        endpoint = 'media/%(media_id)s/info/' % {'media_id': media_id}
        res = self._call_api(endpoint)
        if self.auto_patch:
            [ClientCompatPatch.media(m, drop_incompat_keys=self.drop_incompat_keys)
             for m in res.get('items', [])]
        return res

    def medias_info(self, media_ids):
        """
        Get multiple media infos

        :param media_ids: list of media ids
        :return:
        """
        if isinstance(media_ids, str):
            media_ids = [media_ids]

        params = {
            '_uuid': self.uuid,
            '_csrftoken': self.csrftoken,
            'media_ids': ','.join(media_ids),
            'ranked_content': 'true'
        }
        res = self._call_api('media/infos/', params=params, unsigned=True)
        if self.auto_patch:
            [ClientCompatPatch.media(m, drop_incompat_keys=self.drop_incompat_keys)
             for m in res.get('items', [])]
        return res

    def media_permalink(self, media_id):
        """
        Get media permalink

        :param media_id:
        :return:
        """
        endpoint = 'media/%(media_id)s/permalink/' % {'media_id': media_id}
        res = self._call_api(endpoint)
        return res

    def media_comments(self, media_id, **kwargs):
        """
        Get media comments. Fixed at 20 comments returned per page.

        :param media_id: Media id
        :param kwargs:
            **max_id**: For pagination
        :return:
        """
        endpoint = 'media/%(media_id)s/comments/' % {'media_id': media_id}
        res = self._call_api(endpoint, query=kwargs)

        if self.auto_patch:
            [ClientCompatPatch.comment(c, drop_incompat_keys=self.drop_incompat_keys)
             for c in res.get('comments', [])]
        return res

    def media_n_comments(self, media_id, n=150, reverse=False, **kwargs):
        """
        Helper method to retrieve n number of comments for a media id

        :param media_id: Media id
        :param n: Minimum number of comments to fetch
        :param reverse: Reverse list of comments (ordered by created_time)
        :param kwargs:
        :return:
        """

        endpoint = 'media/%(media_id)s/comments/' % {'media_id': media_id}

        comments = []
        results = self._call_api(endpoint, query=kwargs)
        comments.extend(results.get('comments', []))
        while results.get('has_more_comments') and results.get('next_max_id') and len(comments) < n:
            kwargs.update({'max_id': results.get('next_max_id')})
            results = self._call_api(endpoint, query=kwargs)
            comments.extend(results.get('comments', []))
            if not results.get('next_max_id') or not results.get('comments'):
                # bail out if no max_id or comments returned
                break

        if self.auto_patch:
            [ClientCompatPatch.comment(c, drop_incompat_keys=self.drop_incompat_keys)
             for c in comments]

        return sorted(comments, key=lambda k: k['created_time'], reverse=reverse)

    def edit_media(self, media_id, caption, usertags=[]):
        """
        Edit a media's caption

        :param media_id: Media id
        :param caption: Caption text
        :param usertags: array of user_ids and positions in the format below:

            .. code-block:: javascript

                usertags = [
                    {"user_id":4292127751, "position":[0.625347,0.4384531]}
                ]
        :return:
        """
        endpoint = 'media/%(media_id)s/edit_media/' % {'media_id': media_id}
        params = {'caption_text': caption}
        params.update(self.authenticated_params)
        if usertags:
            utags = {'in': [{'user_id': u['user_id'], 'position': u['position']} for u in usertags]}
            params['usertags'] = json.dumps(utags, separators=(',', ':'))
        res = self._call_api(endpoint, params=params)
        if self.auto_patch:
            ClientCompatPatch.media(res.get('media'))
        return res

    def delete_media(self, media_id):
        """
        Delete a media

        :param media_id: Media id
        :return:
            .. code-block:: javascript

                {"status": "ok", "did_delete": true}
        """
        endpoint = 'media/%(media_id)s/delete/' % {'media_id': media_id}
        params = {'media_id': media_id}
        params.update(self.authenticated_params)
        return self._call_api(endpoint, params=params)

    def post_comment(self, media_id, comment_text):
        """
        Post a comment.
        Comment text validation according to https://www.instagram.com/developer/endpoints/comments/#post_media_comments

        :param media_id: Media id
        :param comment_text: Comment text
        :return:
            .. code-block:: javascript

                {
                  "comment": {
                    "status": "Active",
                    "media_id": 123456789,
                    "text": ":)",
                    "created_at": 1479453671.0,
                    "user": {
                      "username": "x",
                      "has_anonymous_profile_picture": false,
                      "profile_pic_url": "http://scontent-sit4-1.cdninstagram.com/abc.jpg",
                      "full_name": "x",
                      "pk": 123456789,
                      "is_verified": false,
                      "is_private": false
                    },
                    "content_type": "comment",
                    "created_at_utc": 1479482471,
                    "pk": 17865505612040669,
                    "type": 0
                  },
                  "status": "ok"
                }
        """

        if len(comment_text) > 300:
            raise ValueError('The total length of the comment cannot exceed 300 characters.')
        if re.search(r'[a-z]+', comment_text, re.IGNORECASE) and comment_text == comment_text.upper():
            raise ValueError('The comment cannot consist of all capital letters.')
        if len(re.findall(r'#[^#]+\b', comment_text, re.UNICODE | re.MULTILINE)) > 4:
            raise ValueError('The comment cannot contain more than 4 hashtags.')
        if len(re.findall(r'\bhttps?://\S+\.\S+', comment_text)) > 1:
            raise ValueError('The comment cannot contain more than 1 URL.')

        endpoint = 'media/%(media_id)s/comment/' % {'media_id': media_id}
        params = {
            'comment_text': comment_text,
            'user_breadcrumb': gen_user_breadcrumb(len(comment_text)),
            'idempotence_token': self.generate_uuid(),
            'containermodule': 'comments_feed_timeline'
        }
        params.update(self.authenticated_params)
        res = self._call_api(endpoint, params=params)
        if self.auto_patch:
            ClientCompatPatch.comment(res['comment'], drop_incompat_keys=self.drop_incompat_keys)
        return res

    def delete_comment(self, media_id, comment_id):
        """
        Delete a comment

        :param media_id: Media id
        :param comment_id: Comment id
        :return:
            .. code-block:: javascript

                {"status": "ok"}
        """
        endpoint = 'media/%(media_id)s/comment/%(comment_id)s/delete/' % {
            'media_id': media_id, 'comment_id': comment_id}
        params = {}
        params.update(self.authenticated_params)
        res = self._call_api(endpoint, params=params)
        return res

    def media_likers(self, media_id, **kwargs):
        """
        Get users who have liked a post

        :param media_id:
        :return:
        """
        endpoint = 'media/%(media_id)s/likers/' % {'media_id': media_id}
        res = self._call_api(endpoint, query=kwargs)
        if self.auto_patch:
            [ClientCompatPatch.list_user(u, drop_incompat_keys=self.drop_incompat_keys)
             for u in res.get('users', [])]
        return res

    def media_likers_chrono(self, media_id):
        """
        Get users who have liked a post in chronological order

        :param media_id:
        :return:
        """
        res = self._call_api('media/%(media_id)s/likers_chrono/' % {'media_id': media_id})
        if self.auto_patch:
            [ClientCompatPatch.list_user(u, drop_incompat_keys=self.drop_incompat_keys)
             for u in res.get('users', [])]
        return res

    def post_like(self, media_id):
        """
        Like a post

        :param media_id: Media id
        :return:
            .. code-block:: javascript

                {"status": "ok"}
        """
        endpoint = 'media/%(media_id)s/like/' % {'media_id': media_id}
        params = {'media_id': media_id}
        params.update(self.authenticated_params)
        res = self._call_api(endpoint, params=params)
        return res

    def delete_like(self, media_id):
        """
        Unlike a post

        :param media_id:
        :return:
            .. code-block:: javascript

                {"status": "ok"}
        """
        endpoint = 'media/%(media_id)s/unlike/' % {'media_id': media_id}
        params = {'media_id': media_id}
        params.update(self.authenticated_params)
        res = self._call_api(endpoint, params=params)
        return res

    def media_seen(self, reels):
        """
        Mark multiple stories as seen

        :param reels: A dict of media_ids and timings

            .. code-block:: javascript

                {
                    "1309763051087626108_124317": "1470355944_1470372029",
                    "1309764045355643149_124317": "1470356063_1470372039",
                    "1309818450243415912_124317": "1470362548_1470372060",
                    "1309764653429046112_124317": "1470356135_1470372049",
                    "1309209597843679372_124317": "1470289967_1470372013"
                }

                where
                    1309763051087626108_124317 = <media_id>,
                    1470355944_1470372029 is <media_created_time>_<view_time>

        :return:
        """
        params = {'nuxes': {}, 'reels': reels}
        params.update(self.authenticated_params)
        res = self._call_api('media/seen/', params=params)
        return res

    def comment_like(self, comment_id):
        """
        Like a comment

        :param comment_id:

        :return:
            .. code-block:: javascript

                {"status": "ok"}
        """
        endpoint = 'media/%(comment_id)s/comment_like/' % {'comment_id': comment_id}
        params = self.authenticated_params
        return self._call_api(endpoint, params=params)

    def comment_likers(self, comment_id):
        """
        Get users who have liked a comment

        :param comment_id:
        :return:
        """
        endpoint = 'media/%(comment_id)s/comment_likers/' % {'comment_id': comment_id}
        res = self._call_api(endpoint)
        if self.auto_patch:
            [ClientCompatPatch.list_user(u, drop_incompat_keys=self.drop_incompat_keys)
             for u in res.get('users', [])]
        return res

    def comment_unlike(self, comment_id):
        """
        Unlike a comment

        :param comment_id:
        :return:
            .. code-block:: javascript

                {"status": "ok"}
        """
        endpoint = 'media/%(comment_id)s/comment_unlike/' % {'comment_id': comment_id}
        params = self.authenticated_params
        return self._call_api(endpoint, params=params)

    def save_photo(self, media_id):
        """
        Save a photo

        :param media_id: Media id
        :return:
            .. code-block:: javascript

                {"status": "ok"}
        """
        endpoint = 'media/%(media_id)s/save/' % {'media_id': media_id}
        params = {'radio_type': 'WIFI'}
        params.update(self.authenticated_params)
        return self._call_api(endpoint, params=params)

    def unsave_photo(self, media_id):
        """
        Unsave a photo

        :param media_id:
        :return:
            .. code-block:: javascript

                {"status": "ok"}
        """
        endpoint = 'media/%(media_id)s/unsave/' % {'media_id': media_id}
        params = {'radio_type': 'WIFI'}
        params.update(self.authenticated_params)
        return self._call_api(endpoint, params=params)

    def disable_comments(self, media_id):
        """
        Disable comments for a media

        :param media_id:
        :return:
            .. code-block:: javascript

                {"status": "ok"}
        """
        endpoint = 'media/%(media_id)s/disable_comments/' % {'media_id': media_id}
        params = {
            '_csrftoken': self.csrftoken,
            '_uuid': self.uuid,
        }
        res = self._call_api(endpoint, params=params, unsigned=True)
        return res

    def enable_comments(self, media_id):
        """
        Enable comments for a media

        :param media_id:
        :return:
            .. code-block:: javascript

                {"status": "ok"}
        """

        endpoint = 'media/%(media_id)s/enable_comments/' % {'media_id': media_id}
        params = {
            '_csrftoken': self.csrftoken,
            '_uuid': self.uuid,
        }
        res = self._call_api(endpoint, params=params, unsigned=True)
        return res
