import { Telegraf, Markup } from 'telegraf';
import * as dotenv from 'dotenv';
import { UserStore } from './userStore';
import { MeetupStore } from './meetupStore';
import { PointEventStore } from './pointEventStore';

dotenv.config();

const bot = new Telegraf(process.env.BOT_TOKEN!);
const ADMIN_ID = Number(process.env.ADMIN_ID);

const pointEvents = new PointEventStore();
const store = new UserStore();
const meetups = new MeetupStore();

bot.start((ctx) => {
  const { id, username, first_name } = ctx.from;
  const args = ctx.message.text.split(' ');
  const meetupId = args[1];

  store.addUser({ id, username, name: first_name });

  if (meetupId) {
    const m = meetups.get(meetupId);
    if (!m) return ctx.reply(`Митап не найден ❌`);
    if (!m.active) return ctx.reply(`Митап "${m.name}" пока не активен 🚧`);

    const alreadyClaimed = pointEvents.hasEvent(id, 'meetup_attendance', meetupId);
    if (alreadyClaimed) {
      return ctx.reply(`Ты уже получил поинты за митап "${m.name}" 😉`);
    }

    // начисляем
    pointEvents.add({
      userId: id,
      type: 'meetup_attendance',
      meetupId,
      points: m.points,
      timestamp: new Date().toISOString()
    });

    ctx.reply(`🎉 Ты получил ${m.points} поинтов за участие в "${m.name}"`);
  }

  return sendMainMenu(ctx);
});

async function sendMainMenu(ctxOrCallback: any) {
  const id = ctxOrCallback.from.id;
  const name = ctxOrCallback.from.first_name;
  const points = pointEvents.getUserPoints(id);

  const text = `Привет, ${name}!\n\n🎯 Твои поинты: ${points}`;

  const buttons = [
    [Markup.button.callback('🔁 Обновить', 'refresh')],
  ];

  if (id === ADMIN_ID) {
    buttons.push([Markup.button.callback('⚙️ Админка', 'admin_menu')]);
  }

  await ctxOrCallback.reply(text, Markup.inlineKeyboard(buttons));
}

bot.action('refresh', async (ctx) => {
  await sendMainMenu(ctx);
});

bot.launch();
