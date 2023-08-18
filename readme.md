# The Classy Discord Bot

### How to use:
 - Create a `.env` file similar to `example.env`
 - Change `DISCORD_TOKEN` to your discord token

### How to enable the imagine command:
- Create a [mage.space](https://mage.space) account
- Run the script below in your browser's developer console to get the refresh token
- Put the refresh token in `MAGE_REFRESH_TOKEN` in `.env`

```javascript
indexedDB.open("firebaseLocalStorageDb").onsuccess = (event) => {
    var db = event.target.result;
    var transaction = db.transaction("firebaseLocalStorage");
    transaction.objectStore("firebaseLocalStorage").openCursor().onsuccess = (event) => {
        console.log("Refresh Token:", event.target.result.value.value.stsTokenManager.refreshToken);
    };
    transaction.oncomplete = (event) => {
        db.close();
    };
};
```