import Link from "next/link"

export const metadata = {
  title: "מדיניות פרטיות — ShiftWise",
}

export default function PrivacyPolicyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 leading-relaxed" dir="rtl">
      <Link href="/" className="text-sm text-blue-600 hover:underline">
        ← חזרה לדף הראשי
      </Link>

      <h1 className="mt-4 text-3xl font-bold">מדיניות פרטיות</h1>
      <p className="mt-2 text-sm text-gray-500">עודכן לאחרונה: מאי 2026</p>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">1. מי אנחנו</h2>
        <p>
          ShiftWise (להלן: <strong>"השירות"</strong>) היא מערכת לניהול סידור משמרות
          וזמינות עובדים, המופעלת מישראל. השירות מיועד לעסקים שמעסיקים עובדים
          במשמרות (מסעדות, בתי קפה, רשתות קמעונאיות וכד׳).
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">2. אילו נתונים אנו אוספים</h2>
        <ul className="list-disc space-y-2 pr-6">
          <li>
            <strong>פרטי זיהוי:</strong> שם מלא, מספר טלפון, אימייל, תפקיד בעסק.
          </li>
          <li>
            <strong>נתוני זמינות וסידור:</strong> הצהרות זמינות שבועיות, משמרות
            ששובצת אליהן, בקשות החלפה.
          </li>
          <li>
            <strong>נתוני נוכחות (אופציונלי):</strong> זמני כניסה ויציאה ממשמרת,
            מיקום GPS מקורב בעת הכניסה (רק אם תאשר ממכשירך).
          </li>
          <li>
            <strong>תקשורת ב-WhatsApp:</strong> הודעות שאתה שולח לבוט שלנו ושאנו
            שולחים אליך (לצורך תפעול הסידור).
          </li>
          <li>
            <strong>נתוני שימוש טכניים:</strong> סוג דפדפן, כתובת IP, זמני
            פעילות — לצורך אבטחת מידע ושיפור השירות.
          </li>
        </ul>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">3. למה אנו משתמשים בנתונים</h2>
        <ul className="list-disc space-y-2 pr-6">
          <li>בנייה ושליחה של סידורי משמרות.</li>
          <li>שליחת תזכורות והודעות תפעוליות ב-WhatsApp.</li>
          <li>חישוב שעות עבודה ומשכורת משוערת (לעסק שמעסיק אותך).</li>
          <li>אבטחת מידע, מניעת הונאות, וניתוח באגים.</li>
        </ul>
        <p>
          <strong>אנו לא מוכרים נתונים לצדדים שלישיים</strong> ולא משתמשים בהם
          לפרסום ממוקד.
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">4. שיתוף עם ספקי שירות</h2>
        <p>חלק מהנתונים מועברים לספקי תשתית טכנית הפועלים בשמנו:</p>
        <ul className="list-disc space-y-2 pr-6">
          <li><strong>Railway</strong> — אחסון השרתים ומסד הנתונים.</li>
          <li><strong>Twilio / Meta WhatsApp</strong> — שליחת וקבלת הודעות WhatsApp.</li>
          <li><strong>Sentry</strong> — מעקב טכני אחר תקלות (ללא תוכן אישי).</li>
        </ul>
        <p>כל אחד מהם כפוף להסכמי סודיות ומדיניות פרטיות משלו.</p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">5. שמירה ומחיקה של נתונים</h2>
        <p>
          נתוני זמינות, סידור ונוכחות נשמרים במשך תקופת ההעסקה שלך + 7 שנים,
          בהתאם לחוק החובה לשמירת רישומי עבודה בישראל.
        </p>
        <p>
          תוכל לבקש בכל עת:
        </p>
        <ul className="list-disc space-y-2 pr-6">
          <li>לקבל עותק מכל הנתונים שלך.</li>
          <li>לתקן נתונים שגויים.</li>
          <li>למחוק את כל הנתונים (פרט לאלה ששמירתם נדרשת בחוק).</li>
        </ul>
        <p>
          לבקשה, פנה למנהל העסק שלך, או שלח אימייל ל:{" "}
          <a href="mailto:privacy@shiftwise.app" className="text-blue-600 hover:underline">
            privacy@shiftwise.app
          </a>
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">6. אבטחת מידע</h2>
        <p>
          אנו משתמשים בסיסמאות מוצפנות (bcrypt), הצפנת TLS לכל תקשורת, ובדיקות
          חתימה לכל webhook נכנס. סיסמת המערכת חייבת להיות באורך 8 תווים לפחות.
        </p>
        <p>
          במקרה של אירוע אבטחה, נודיע למשתמשים שנפגעו תוך 72 שעות מרגע הגילוי.
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">7. חוקים החלים</h2>
        <p>
          השירות פועל בכפיפות לחוק הגנת הפרטיות, התשמ"א-1981, ולתקנות הגנת
          הפרטיות (אבטחת מידע), התשע"ז-2017.
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">8. שינויים במדיניות</h2>
        <p>
          אם נשנה את המדיניות באופן מהותי, נודיע לכך בהתחברות הבאה ונבקש את
          הסכמתך מחדש. שינויים קוסמטיים יתעדכנו ללא הודעה.
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">9. יצירת קשר</h2>
        <p>
          לשאלות, בקשות, או תלונות:{" "}
          <a href="mailto:privacy@shiftwise.app" className="text-blue-600 hover:underline">
            privacy@shiftwise.app
          </a>
        </p>
      </section>

      <p className="mt-12 text-xs text-gray-500">
        מסמך זה הוא תקציר משפטי בלבד. ייתכן שנדרשות התאמות נוספות לעסקך
        הספציפי — מומלץ להתייעץ עם עו"ד.
      </p>
    </div>
  )
}
