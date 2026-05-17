/*
  Planora temporary Firebase web push service worker.

  Before testing, replace the firebaseConfig values below with the same Firebase web app
  config used in firebase_token_test.html.
*/

importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js");

const firebaseConfig = {
  apiKey: "PASTE_API_KEY",
  authDomain: "PASTE_PROJECT.firebaseapp.com",
  projectId: "PASTE_PROJECT_ID",
  storageBucket: "PASTE_PROJECT.appspot.com",
  messagingSenderId: "PASTE_SENDER_ID",
  appId: "PASTE_APP_ID",
};

firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const notification = payload.notification || {};
  const title = notification.title || "Planora";
  const options = {
    body: notification.body || "You have a new Planora notification.",
    data: payload.data || {},
  };

  self.registration.showNotification(title, options);
});
