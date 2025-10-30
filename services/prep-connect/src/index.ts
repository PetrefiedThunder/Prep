import app from './server';

const port = Number.parseInt(process.env.PORT ?? '4002', 10);

app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`prep-connect service listening on port ${port}`);
});
