import { Telegraf, Markup } from 'telegraf';
import * as dotenv from 'dotenv';

dotenv.config();

const bot = new Telegraf(process.env.BOT_TOKEN!);
const ADMIN_ID = Number(process.env.ADMIN_ID);

// In-memory хранилище поинтов: userId -> points
const users: Record<number, number> = {};

function getPoints(id: number) {
  return users[id] ?? 0;
}

function addPoints(id: number, amount = 1) {
  users[id] = getPoints(id) + amount;
}

// Главный экран
async function sendMainMenu(ctxOrCallback: any) {
  const id = ctxOrCallback.from.id;
  const name = ctxOrCallback.from.first_name;
  const points = getPoints(id);

  const text = `Привет, ${name}!\n\n🎯 Твои поинты: ${points}`;

  const buttons = [
    // [Markup.button.callback('🎁 Получить поинт', 'get_point')],
    // [Markup.button.callback('📊 Топ участников', 'show_top')],
    [Markup.button.callback('🔁 Обновить', 'refresh')],
  ];

  if (id === ADMIN_ID) {
    buttons.push([Markup.button.callback('⚙️ Админка', 'admin_menu')]);
  }

  await ctxOrCallback.reply(text, Markup.inlineKeyboard(buttons));
}

// /start
bot.start((ctx) => {
  addPoints(ctx.from.id, 0); // создать запись если нет
  return sendMainMenu(ctx);
});

// Кнопка: Получить поинт
bot.action('get_point', async (ctx) => {
  addPoints(ctx.from.id, 1);
  await sendMainMenu(ctx);
});

// Кнопка: Обновить
bot.action('refresh', async (ctx) => {
  await sendMainMenu(ctx);
});

// Кнопка: Топ
bot.action('show_top', async (ctx) => {
  const top = Object.entries(users)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .map(([id, pts], i) => `${i + 1}. ID ${id}: ${pts} pts`)
    .join('\n');

  const text = `📊 Топ участников:\n\n${top || 'Пока пусто'}`;

  await ctx.reply(text, Markup.inlineKeyboard([
    [Markup.button.callback('⬅️ Назад', 'refresh')],
  ]));
});

bot.launch();
