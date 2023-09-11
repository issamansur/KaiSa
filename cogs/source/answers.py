class ANSWERS:
    def __f(answer: str) -> str:
        return f"```> {answer}```"

    IS_CHAT: str = __f("Эта функция работает только на едине со мной...")
    IS_NOT_GUILD: str = __f("Ты скорее всего со мной в личных сообщениях")
    NO_VOICE_USER: str = __f("Глупенький. Зайди сначала в голосовой канал ^^")
    NO_VOICE_BOT: str = __f("Сначала пригласи меня к себе, потом командуй...")
    JUST_THERE: str = __f("Я уже тут... и готова к приказам...")
    JUST_BUSY: str = __f("Шшш... Сейчас меня трогает другой...")

    GREETING: str = __f("Привет, семпай ~")
    ON_JOIN: str = __f("Зашла к тебе в комнату... к тебе...")
    ON_SEARCH: str = __f("Поиск по запросу...")
    ON_FOUND: str = __f("Результат(ы) поиска:")
    ON_NOT_FOUND: str = __f("Ничего не найдено ._.")

    ON_ADDING_TRACK: str = __f("Трек добавлен")
    ON_LIST_EMPTY: str = __f("Список пуст...")
    ON_LIST_FULL: str = __f("В очереди уже 15 треков!")

    ON_PLAY: str = __f("Приятного прослушивания, семпай...")
    ON_REPEAT: str = __f("")
    ON_SKIP: str = __f("Переключаю трек...")
    ON_END: str = __f("Я кончи... Кхм. Закончила...")
    ON_QUIT: str = __f("Уф. Ты меня так измотал~")

    NO_SERVICE: str = (
        "Аудио сервис не подключен. Для авторизации пропишите ```/register```"
    )
    INVALID_REPEAT_TYPE: str = __f("Допустимые параметры: one, all, off")
