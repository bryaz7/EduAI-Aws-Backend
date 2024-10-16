from typing import Dict

from utils.enum.language import Language

openai_error_message = {
    Language.ENGLISH: "My brain somehow collapsed, could you ask me again?",
    Language.SPANISH: "Mi cerebro de alguna manera colapsó, ¿podrías preguntarme de nuevo?",
    Language.FRENCH: "Mon cerveau a d'une certaine manière fait un bug, pourrais-tu me poser la question à nouveau ?",
    Language.HINDI: "मेरा मस्तिष्क किसी तरह से टकरा गया है, क्या आप मुझसे फिर से पूछ सकते हैं?",
    Language.ITALIAN: "Il mio cervello ha in qualche modo avuto un cedimento, potresti farmi la domanda di nuovo?",
    Language.GERMAN: "Mein Gehirn ist irgendwie zusammengebrochen, könntest du mich nochmal fragen?",
    Language.POLISH: "Mój mózg jakoś zawalił się, czy mógłbyś zadać mi pytanie ponownie?",
    Language.PORTUGUESE: "Meu cérebro de alguma forma colapsou, você poderia me perguntar novamente?"
}

stability_ai_error_message = {
    Language.ENGLISH: "I'm planning to draw some awesome thing, but I lost my painting brush. Can you re-enter what you have just asked?",
    Language.SPANISH: "Estoy planeando dibujar algo increíble, pero perdí mi pincel. ¿Podrías volver a decirme lo que acabas de preguntar?",
    Language.FRENCH: "Je prévois de dessiner quelque chose d'incroyable, mais j'ai perdu mon pinceau. Pouvez-vous répéter ce que vous venez de demander ?",
    Language.HINDI: "मैं कुछ बढ़िया चीज़ बनाने की योजना बना रहा हूँ, लेकिन मेरा पेंटिंग ब्रश खो गया है। क्या आप जो आपने अभी पूछा था वह फिर से बता सकते हैं?",
    Language.ITALIAN: "Sto progettando di disegnare qualcosa di fantastico, ma ho perso il mio pennello. Puoi ripetere ciò che hai appena chiesto?",
    Language.GERMAN: "Ich plane, etwas Tolles zu zeichnen, aber ich habe meinen Pinsel verloren. Kannst du bitte wiederholen, was du gerade gefragt hast?",
    Language.POLISH: "Planuję narysować coś niesamowitego, ale zgubiłem pędzel. Czy możesz powtórzyć to, o co właśnie zapytałeś?",
    Language.PORTUGUESE: "Estou planejando desenhar algo incrível, mas perdi meu pincel de pintura. Você poderia reentrar o que você acabou de perguntar?"
}

boto3_error_message = {
    Language.ENGLISH: "I'm being locked in my room. Can you send a Report with content `Boto3` using the Report button at the bottom right corner?",
    Language.SPANISH: "Estoy siendo encerrado en mi habitación. ¿Puedes enviar un informe con el contenido 'Boto3' utilizando el botón de Informe en la esquina inferior derecha?",
    Language.FRENCH: "Je suis enfermé dans ma chambre. Pouvez-vous envoyer un rapport avec le contenu `Boto3` en utilisant le bouton de rapport en bas à droite ?",
    Language.HINDI: "मुझे अपने कमरे में बंद कर दिया जा रहा है। क्या आप बॉटो 3 के साथ सामग्री के साथ एक रिपोर्ट भेज सकते हैं, जो नीचे दाहिने कोने में स्थित रिपोर्ट बटन का उपयोग करता है?",
    Language.ITALIAN: "Sto venendo rinchiuso nella mia stanza. Puoi inviare una segnalazione con il contenuto `Boto3` utilizzando il pulsante Segnala in basso a destra?",
    Language.GERMAN: "Ich werde in meinem Zimmer eingeschlossen. Kannst du einen Bericht mit dem Inhalt 'Boto3' senden, indem du den Berichtsbutton in der unteren rechten Ecke verwendest?",
    Language.POLISH: "Zostaję zamknięty w swoim pokoju. Czy możesz wysłać raport z treścią `Boto3`, korzystając z przycisku Raportu w prawym dolnym rogu?",
    Language.PORTUGUESE: "Estou sendo trancado no meu quarto. Você pode enviar um Relatório com o conteúdo 'Boto3' usando o botão de Relatório no canto inferior direito?"
}

default_error_message = {
    Language.ENGLISH: "Could you repeat the question? If you have repeated, you can send a report using the Report button at the bottom right corner.",
    Language.SPANISH: "¿Podrías repetir la pregunta? Si ya la has repetido, puedes enviar un informe utilizando el botón de Informe en la esquina inferior derecha.",
    Language.FRENCH: "Pourriez-vous répéter la question ? Si vous l'avez déjà répétée, vous pouvez envoyer un rapport en utilisant le bouton de rapport en bas à droite.",
    Language.HINDI: "क्या आप सवाल दोहरा सकते हैं? अगर आपने दोहराया है, तो आप नीचे दाहिने कोने में स्थित रिपोर्ट बटन का उपयोग करके रिपोर्ट भेज सकते हैं।",
    Language.ITALIAN: "Potresti ripetere la domanda? Se l'hai già ripetuta, puoi inviare una segnalazione utilizzando il pulsante Segnala in basso a destra.",
    Language.GERMAN: "Könntest du die Frage wiederholen? Wenn du sie bereits wiederholt hast, kannst du einen Bericht mit dem Berichtsbutton in der unteren rechten Ecke senden.",
    Language.POLISH: "Czy mógłbyś powtórzyć pytanie? Jeśli powtórzyłeś, możesz wysłać raport, korzystając z przycisku Raportu w prawym dolnym rogu.",
    Language.PORTUGUESE: "Você poderia repetir a pergunta? Se já repetiu, pode enviar um relatório usando o botão de Relatório no canto inferior direito."
}

wrong_image_format_error_message = {
    Language.ENGLISH: "I think you put the image with the incorrect format. It should have the extension of .png, .jpg, or .jpeg. If you really want to input this image, search the web for converting it into the correct format.",
    Language.SPANISH: "Creo que has puesto la imagen con el formato incorrecto. Debería tener la extensión .png, .jpg o .jpeg. Si realmente quieres usar esta imagen, busca en la web cómo convertirla al formato correcto.",
    Language.FRENCH: "Je pense que tu as mis l'image avec le mauvais format. Elle devrait avoir l'extension .png, .jpg ou .jpeg. Si tu veux vraiment utiliser cette image, recherche sur le web comment la convertir dans le bon format.",
    Language.HINDI: "मुझे लगता है आपने गलत फ़ॉर्मेट के साथ छवि डाली है। इसे .png, .jpg या .jpeg का एक्सटेंशन होना चाहिए। यदि आप वास्तव में इस छवि को इनपुट करना चाहते हैं, तो ठीक फ़ॉर्मेट में इसे परिवर्तित करने के लिए वेब में खोजें।",
    Language.ITALIAN: "Penso che tu abbia inserito l'immagine con il formato sbagliato. Dovrebbe avere l'estensione .png, .jpg o .jpeg. Se desideri veramente inserire questa immagine, cerca sul web come convertirla nel formato corretto.",
    Language.GERMAN: "Ich glaube, du hast das Bild im falschen Format hochgeladen. Es sollte die Erweiterung .png, .jpg oder .jpeg haben. Wenn du das Bild wirklich verwenden möchtest, suche im Internet nach einer Konvertierung in das richtige Format.",
    Language.POLISH: "Myślę, że dodałeś obraz w niewłaściwym formacie. Powinien mieć rozszerzenie .png, .jpg lub .jpeg. Jeśli naprawdę chcesz użyć tego obrazu, poszukaj w sieci narzędzia do konwersji go na właściwy format.",
    Language.PORTUGUESE: "Acredito que você colocou a imagem com o formato incorreto. Ela deve ter a extensão .png, .jpg ou .jpeg. Se realmente deseja inserir esta imagem, pesquise na web como convertê-la para o formato correto."
}

invalid_image_error_message = {
    Language.ENGLISH: "The image you sent is quite small, try again with a bigger one.",
    Language.SPANISH: "La imagen que enviaste es bastante pequeña, intenta de nuevo con una más grande.",
    Language.FRENCH: "L'image que vous avez envoyée est assez petite, essayez à nouveau avec une plus grande.",
    Language.HINDI: "आपने जो छवि भेजी है वह काफी छोटी है, एक बड़ी छवि के साथ पुनः प्रयास करें।",
    Language.ITALIAN: "L'immagine che hai inviato è piuttosto piccola, prova di nuovo con una più grande.",
    Language.GERMAN: "Das von Ihnen gesendete Bild ist ziemlich klein, versuchen Sie es nochmal mit einem größeren Bild.",
    Language.POLISH: "Zdjęcie, które wysłałeś, jest dość małe, spróbuj ponownie z większym.",
    Language.PORTUGUESE: "A imagem que você enviou é bem pequena, tente novamente com uma maior."
}


def retrieve_error_message(language: str, template: Dict):
    language = Language.value_of(language)
    return template.get(language, template[Language.ENGLISH])


def get_default_openai_error_message(language: str):
    return retrieve_error_message(language, openai_error_message)


def get_default_stability_ai_error_message(language: str):
    return retrieve_error_message(language, stability_ai_error_message)


def get_default_boto3_error_message(language: str):
    return retrieve_error_message(language, boto3_error_message)


def get_default_error_message(language: str):
    return retrieve_error_message(language, default_error_message)


def get_default_wrong_image_format_message(language: str):
    return retrieve_error_message(language, wrong_image_format_error_message)


def get_default_small_image_message(language: str):
    return retrieve_error_message(language, invalid_image_error_message)


def get_default_language_incompatible_message(supported_languages):
    return "Are you asking in a language other than {}? If yes, retry with supported languages or upgrade to a " \
           "better package.".format(', '.join(supported_languages))


class QueryNotFoundError(Exception):
    pass


class ItemNotFoundError(QueryNotFoundError):
    pass


class ConversationNotFoundError(QueryNotFoundError):
    pass


class ActionNotFoundError(QueryNotFoundError):
    pass


class StyleNotFoundError(QueryNotFoundError):
    pass


class MediaNotFoundError(QueryNotFoundError):
    pass


class DuplicatedPackageFoundError(QueryNotFoundError):
    pass


class UserNotFoundError(QueryNotFoundError):
    pass


class PackageNotFoundError(QueryNotFoundError):
    pass


class OutOfQuotaError(Exception):
    pass


class StripePaymentException(Exception):
    pass


class StabilityAIRequestError(Exception):
    pass


class LanguageIncompatibleError(Exception):
    pass


class NotificationGenerationError(Exception):
    pass


class ValidationError(Exception):
    pass


class InvalidImageInput(Exception):
    pass


class BadRequestError(Exception):
    pass
