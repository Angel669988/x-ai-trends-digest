# WeChat Official Account Publish (Draft -> Publish)

This workflow uses server-side endpoints (provided by user):

## 1) Get access_token
GET https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=APPID&secret=APPSECRET

## 2) Upload article images (for content)
POST https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=ACCESS_TOKEN
- form-data: media=@image.jpg
- response: { "url": "http://mmbiz.qpic.cn/XXXXX" }

## 3) Upload permanent material (cover)
POST https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=ACCESS_TOKEN&type=thumb
- form-data: media=@cover.jpg
- response: { "media_id": "MEDIA_ID", "url": "https://..." }

## 4) Add draft
POST https://api.weixin.qq.com/cgi-bin/draft/add?access_token=ACCESS_TOKEN
- body: { articles: [ { article_type:"news", title, author, digest, content, content_source_url, thumb_media_id, need_open_comment, only_fans_can_comment } ] }
- response: { "media_id": "MEDIA_ID" }

## 5) Publish draft
POST https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token=ACCESS_TOKEN
- body: { "media_id": "MEDIA_ID" }
- response: { errcode, errmsg, publish_id, msg_data_id }

## Notes
- `thumb_media_id` must be a permanent media id (cover image) for article_type `news`.
- Content must be HTML; images inside content must use URLs from `uploadimg`.
