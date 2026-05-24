import Link from "next/link"

export const metadata = {
  title: "תנאי שימוש — ShiftWise",
}

export default function TermsOfServicePage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 leading-relaxed" dir="rtl">
      <Link href="/" className="text-sm text-blue-600 hover:underline">
        ← חזרה לדף הראשי
      </Link>

      <h1 className="mt-4 text-3xl font-bold">תנאי שימוש</h1>
      <p className="mt-2 text-sm text-gray-500">עודכן לאחרונה: מאי 2026</p>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">1. כללי</h2>
        <p>
          תנאי שימוש אלה (להלן: <strong>"התנאים"</strong>) מסדירים את השימוש שלך
          במערכת ShiftWise (להלן: <strong>"השירות"</strong>). השימוש בשירות מהווה
          הסכמה מפורשת לתנאים אלה ולמדיניות הפרטיות שלנו.
        </p>
        <p>
          אם אינך מסכים לתנאים — אנא הימנע משימוש בשירות.
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">2. הגדרת השירות</h2>
        <p>
          ShiftWise הוא שירות SaaS לניהול סידור משמרות, זמינות עובדים, ותקשורת
          עם עובדים באמצעות WhatsApp. השירות מיועד לעסקים שמעסיקים עובדים
          במשמרות (להלן: <strong>"המנוי"</strong>).
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">3. הרשמה וחשבון</h2>
        <ul className="list-disc space-y-2 pr-6">
          <li>הרישום פתוח לעסקים פעילים בלבד הפועלים בישראל.</li>
          <li>אתה מתחייב לספק פרטים נכונים ומדויקים.</li>
          <li>אתה אחראי לשמירת הסיסמה שלך ולכל פעולה שתבוצע מחשבונך.</li>
          <li>במקרה של חשד לפגיעה באבטחת החשבון — דווח לנו מיד.</li>
        </ul>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">4. שימוש מותר</h2>
        <p>אסור להשתמש בשירות לשם:</p>
        <ul className="list-disc space-y-2 pr-6">
          <li>פעילות בלתי-חוקית.</li>
          <li>הטעיה, הונאה, או הפרת זכויות צד ג׳.</li>
          <li>שליחת הודעות ספאם או הודעות מטעות לעובדים.</li>
          <li>ניסיון לגשת לחשבונות אחרים, לפגוע בשירות, או לעקוף הגבלות.</li>
          <li>שימוש שאינו תואם לחוקי העבודה בישראל.</li>
        </ul>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">5. תשלום, חידוש וביטול</h2>
        <ul className="list-disc space-y-2 pr-6">
          <li>השירות מסופק במנוי חודשי לפי החבילה שבחרת.</li>
          <li>החיוב מתבצע מראש בתחילת כל חודש.</li>
          <li>ניתן לבטל את המנוי בכל עת בהודעה בכתב — הביטול ייכנס לתוקף בסוף החודש המחויב.</li>
          <li>לא יבוצעו החזרים יחסיים על חודש שהחל.</li>
          <li>אנו רשאים לעדכן מחירים בהודעה מוקדמת של 30 יום.</li>
        </ul>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">6. זמינות ותחזוקה</h2>
        <p>
          אנו פועלים לספק זמינות גבוהה של השירות, אך לא מתחייבים ל-100% uptime.
          תחזוקה מתוכננת תבוצע בהודעה מוקדמת ככל הניתן.
        </p>
        <p>
          השירות תלוי בצדדים שלישיים (Railway, Twilio, Meta WhatsApp). שיבושים
          אצלם עלולים להשפיע על השירות מבלי שיהיה לנו שליטה ישירה.
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">7. הגבלת אחריות</h2>
        <p>
          השירות מסופק <strong>"AS IS"</strong> ככלי תומך החלטה. <strong>אחריות
          ניהול העובדים, חוקיות הסידור, חישוב המשכורות, ויחסי העבודה — מוטלת
          על המנוי בלבד.</strong>
        </p>
        <p>
          בשום מקרה לא תחול עלינו אחריות על נזק עקיף, אובדן הכנסה, אובדן נתונים,
          או נזק תוצאתי הנובע מהשימוש בשירות. תקרת האחריות המקסימלית שלנו
          מוגבלת לסכום ששילמת בשלושת החודשים האחרונים.
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">8. קניין רוחני</h2>
        <p>
          כל זכויות הקניין הרוחני בשירות (קוד, עיצוב, לוגו, ממשק, אלגוריתמי
          האופטימיזציה) שייכות לנו. אסור להעתיק, להפיץ, או לבצע hand-engineering
          ללא אישור בכתב מאיתנו.
        </p>
        <p>
          הנתונים שאתה מעלה (פרטי עובדים, סידורים, היסטוריה) נשארים <strong>בבעלותך
          המלאה</strong>. אנו מקבלים רישיון מוגבל להשתמש בהם לצורך הפעלת השירות
          בלבד.
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">9. סיום הסכם</h2>
        <p>
          אנו רשאים להשעות או לבטל את החשבון שלך במקרה של:
        </p>
        <ul className="list-disc space-y-2 pr-6">
          <li>הפרת התנאים הללו.</li>
          <li>אי-תשלום במשך יותר מ-14 יום.</li>
          <li>שימוש המסכן את אבטחת השירות או משתמשים אחרים.</li>
        </ul>
        <p>
          במקרה של ביטול ביוזמתך, נשמור על הנתונים שלך 30 יום נוספים לצורך ייצוא,
          ולאחר מכן הם יימחקו בצורה בלתי-הפיכה (אלא אם חובה חוקית מחייבת אחרת).
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">10. שינויים בתנאים</h2>
        <p>
          אנו רשאים לעדכן את התנאים מעת לעת. שינויים מהותיים יידחפו לרישום מחודש
          של הסכמה דרך הממשק. שינויים קוסמטיים יתעדכנו ללא הודעה.
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">11. דין שיפוט וסמכות</h2>
        <p>
          הסכם זה כפוף לדיני מדינת ישראל. סמכות שיפוט בלעדית נתונה לבתי המשפט
          המוסמכים במחוז תל אביב.
        </p>
      </section>

      <section className="mt-8 space-y-4">
        <h2 className="text-xl font-semibold">12. יצירת קשר</h2>
        <p>
          לשאלות, תלונות, או הודעות משפטיות:{" "}
          <a href="mailto:legal@shiftwise.app" className="text-blue-600 hover:underline">
            legal@shiftwise.app
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
