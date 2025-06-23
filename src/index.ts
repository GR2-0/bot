import { Telegraf, Markup } from 'telegraf';
import * as dotenv from 'dotenv';
import { UserStore } from './userStore';
import { MeetupStore } from './meetupStore';

dotenv.config();

const bot = new Telegraf(process.env.BOT_TOKEN!);
const ADMIN_ID = Number(process.env.ADMIN_ID);

const store = new UserStore();
const meetups = new MeetupStore();

bot.start((ctx) => {
  const { id, username, first_name } = ctx.from;
  const args = ctx.message.text.split(' ');
  const meetupId = args[1];

  store.addUser({ id, username, name: first_name });

  if (meetupId) {
    const m = meetups.get(meetupId);
    if (m && m.active) {
      store.addPoints(id, m.points);
    } else if (m && !m.active) {
      return ctx.reply(`Митап "${m.name}" пока не активен 🚧`);
    } else {
      return ctx.reply(`Неверная ссылка. Митап не найден ❌`);
    }
  }

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
