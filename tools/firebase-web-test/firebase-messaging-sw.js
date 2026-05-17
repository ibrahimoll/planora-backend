/*
  Planora temporary Firebase web push service worker.

  Before testing, replace the firebaseConfig values below with the same Firebase web app
  config used in firebase_token_test.html.
*/

importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js");

const firebaseConfig = {
  apiKey: "AIzaSyBdr6C8WSs4kOniyTog-NkostDDK0nNI1k",
  authDomain: "planora-7a684.firebaseapp.com",
  projectId: "planora-7a684",
  storageBucket: "planora-7a684.firebasestorage.app",
  messagingSenderId: "179943761921",
  appId: "1:179943761921:web:7461be36a0dbec1a697800",
  measurementId: "G-9LVRS7MT84"
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
