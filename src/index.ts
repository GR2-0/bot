import { Telegraf, Markup } from 'telegraf';
import * as dotenv from 'dotenv';
import { UserStore } from './userStore';

dotenv.config();

const bot = new Telegraf(process.env.BOT_TOKEN!);
const ADMIN_ID = Number(process.env.ADMIN_ID);

const store = new UserStore();

bot.start((ctx) => {
  const { id, username, first_name } = ctx.from;
  store.addUser({ id, username, name: first_name });
  return sendMainMenu(ctx);
});

async function sendMainMenu(ctxOrCallback: any) {
  const id = ctxOrCallback.from.id;
  const name = ctxOrCallback.from.first_name;
  const points = store.getPoints(id);

  const text = `Привет, ${name}!\n\n🎯 Твои поинты: ${points}`;

  const buttons = [
    [Markup.button.callback('🎁 Получить поинт', 'get_point')],
    [Markup.button.callback('📊 Топ участников', 'show_top')],
    [Markup.button.callback('🔁 Обновить', 'refresh')],
  ];

  if (id === ADMIN_ID) {
    buttons.push([Markup.button.callback('⚙️ Админка', 'admin_menu')]);
  }

  await ctxOrCallback.reply(text, Markup.inlineKeyboard(buttons));
}

bot.action('get_point', async (ctx) => {
  store.addPoints(ctx.from.id, 1);
  await sendMainMenu(ctx);
});

bot.action('refresh', async (ctx) => {
  await sendMainMenu(ctx);
});

bot.action('show_top', async (ctx) => {
  const top = store.getTopUsers();
  const text = `📊 Топ участников:\n\n` +
    top.map((u, i) => `${i + 1}. ${u.name} (${u.username ?? 'без ника'}): ${u.points} pts`).join('\n');

  await ctx.reply(text, Markup.inlineKeyboard([
    [Markup.button.callback('⬅️ Назад', 'refresh')],
  ]));
});

bot.launch();
