export interface PointEvent {
  userId: number;
  type: 'meetup_attendance' | 'meetup_speaker' | 'custom';
  meetupId?: string;  // можно без, если тип не про митап
  points: number;
  timestamp: string;
}
