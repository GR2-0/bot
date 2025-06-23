export interface Meetup {
  id: string;            // хеш, используется как ключ
  name: string;          // "GR 2.0 Июнь"
  date: string;          // ISO строка
  active: boolean;       // можно ли фармить
  points: number;        // сколько даёт
}
