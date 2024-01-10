
# How to Access media_details

The `media_details` dictionary is a complex structure designed to hold all media information for a video project. Here's how to navigate this structure:

## Structure Overview

```json
{
  "video123": {
    "P1": {
      "paragraph": "This is the text of paragraph 1",
      "img_tags": ["nature", "outdoors"],
      "image1": [
        {
          "url": "https://images.pexels.com/photos/2529375/pexels-photo-2529375.jpeg",
          "description": "Woman Spreading Both Her Arms"
        },
        // Additional images...
      ],
      "video1": [
        {
          "url": "https://player.vimeo.com/external/377100374.hd.mp4?s=9ec2ad7114635409a446a74c3321f715ecbdb0fe&profile_id=175&oauth2_token_id=57447761",
          "description": "Woman doing yoga"
        }
        // Additional videos...
      ]
    },
    // Additional paragraphs...
  }
}
```

## Accessing Data

- **Access a Specific Video's Data**: `media_details['video123']`
- **Access a Specific Paragraph's Data**: `media_details['video123']['P1']`
- **Access Paragraph Text**: `media_details['video123']['P1']['paragraph']`
- **Access Image Tags**: `media_details['video123']['P1']['img_tags']`
- **Access First Image**: `media_details['video123']['P1']['image1'][0]`
- **Access First Video**: `media_details['video123']['P1']['video1'][0]`

## Looping Through Data

To iterate through all paragraphs and their media:

```python
for paragraph_key, paragraph_data in media_details['video123'].items():
    print(f"Working on {paragraph_key}")
    paragraph_text = paragraph_data['paragraph']
    image_tags = paragraph_data['img_tags']
    for image_key, images in paragraph_data.items():
        if image_key.startswith('image'):
            for image in images:
                print(image['url'], image['description'])
    # Similar loop for videos...
```

## Modifying Data

- **Update Paragraph Text**: `media_details['video123']['P1']['paragraph'] = "New text"`
- **Add New Image**: `media_details['video123']['P1']['image2'] = [{"url": "new_url", "description": "new_description"}]`

## Conclusion

The `media_details` dictionary is designed to be flexible and comprehensive for handling various media assets across multiple paragraphs or sections of a video project.
