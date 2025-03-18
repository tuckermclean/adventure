class News():
    bulletins = []
    subscribers = {}

    @staticmethod
    def publish(bulletin):
        News.bulletins.append(bulletin)
        for subscriber in News.subscribers.values():
            subscriber.notify_news(bulletin)

    @staticmethod
    def subscribe(character):
        News.subscribers[character.name] = character

