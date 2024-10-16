import re


def handle_highlight_open_search(content, highlighted_content):
    highlight_word = get_text_between_em_tags(highlighted_content)

    if not highlight_word:
        raise ValueError('No highlighted word found between <em> tags.')

    result = wrap_word_with_em_tag(highlight_word[0], content)
    return result


def get_text_between_em_tags(input_string):
    regex = r'<em>(.*?)<\/em>'
    matches = re.findall(regex, input_string)

    texts_between_em_tags = [re.sub(r'</?em>', '', match) for match in matches]
    return texts_between_em_tags


def wrap_word_with_em_tag(word, input_string):
    regex = r'\b{}\b'.format(re.escape(word))
    replaced_string = re.sub(regex, lambda match: '<em>{}</em>'.format(match.group(0)), input_string,
                             flags=re.IGNORECASE)
    return replaced_string
