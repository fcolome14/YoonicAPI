# class TranslationsService:
    
#     @staticmethod
#     def translate(text_key, lang_code="en", **kwargs):
#         translation = HTMLTemplates.translations.get(lang_code, HTMLTemplates.translations["en"])
#         translated_text = translation.get(text_key, text_key)  # Default to key if no translation found
#         return translated_text.format(**kwargs)