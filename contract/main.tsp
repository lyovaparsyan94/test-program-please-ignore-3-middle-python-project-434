import "@typespec/http";
import "@typespec/openapi";

using TypeSpec.Http;

@service(#{ title: "Online Store API" })
namespace OnlineStoreApi;

// ---------- Модели ----------

model Money {
  amount: int32;
  currency: string = "RUB";
}

model Category {
  id: string;
  slug: string;
  name: string;
}

model Product {
  id: string;
  slug: string;
  name: string;
  description: string;
  price: Money;
  categoryId: string;
  imageUrl?: string;
  available: boolean;
}

model PageMeta {
  page: int32;
  perPage: int32;
  total: int32;
  totalPages: int32;
}

model ProductPage {
  items: Product[];
  meta: PageMeta;
}

model Promo {
  id: string;
  title: string;
  text: string;
  product: Product;
}

model User {
  id: string;
  email: string;
}

model OrderItem {
  productId: string;
  productName: string;
  priceAtPurchase: Money;
  quantity: int32;
}

model ShippingDetails {
  method: "delivery" | "pickup";
  recipientName: string;
  phone: string;
  address?: string;
}

model Order {
  id: string;
  status: "paid";
  items: OrderItem[];
  shipping: ShippingDetails;
  total: Money;
  createdAt: utcDateTime;
}

model Health {
  status: string;
}

// ---------- Тела запросов ----------

model Credentials {
  @format("email")
  email: string;

  @minLength(6)
  password: string;
}

model CartItem {
  productId: string;

  @minValue(1)
  quantity: int32;
}

model OrderCreate {
  @minItems(1)
  items: CartItem[];

  shipping: ShippingDetails;
}

// ---------- Ошибки ----------

// Закрытый словарь типов ошибок (RFC 9457). Новый случай начинается
// с правки этого перечисления, а не с новой строки где-то в коде.
enum ProblemType {
  invalidCredentials: "/problems/invalid-credentials",
  emailTaken: "/problems/email-taken",
  addressRequired: "/problems/address-required",
  unavailableItems: "/problems/unavailable-items",
  validationError: "/problems/validation-error",
  unauthorized: "/problems/unauthorized",
  notFound: "/problems/not-found",
  internalError: "/problems/internal-error",
}

@error
model InvalidCredentials {
  @statusCode statusCode: 401;
  type: ProblemType.invalidCredentials;
  title: string;
  detail?: string;
}

@error
model Unauthorized {
  @statusCode statusCode: 401;
  type: ProblemType.unauthorized;
  title: string;
  detail?: string;
}

@error
model EmailTaken {
  @statusCode statusCode: 409;
  type: ProblemType.emailTaken;
  title: string;
  detail?: string;
}

@error
model ValidationError {
  @statusCode statusCode: 400;
  type: ProblemType.validationError;
  title: string;
  detail?: string;
}

@error
model AddressRequired {
  @statusCode statusCode: 400;
  type: ProblemType.addressRequired;
  title: string;
  detail?: string;
}

@error
model UnavailableItems {
  @statusCode statusCode: 400;
  type: ProblemType.unavailableItems;
  title: string;
  detail?: string;
  unavailableProductIds: string[];
}

@error
model NotFound {
  @statusCode statusCode: 404;
  type: ProblemType.notFound;
  title: string;
  detail?: string;
}

@error
model InternalError {
  @statusCode statusCode: 500;
  type: ProblemType.internalError;
  title: string;
  detail?: string;
}

// ---------- Успешные ответы с кодом ----------

model UserCreated {
  @statusCode statusCode: 201;
  ...User;
}

model OrderCreated {
  @statusCode statusCode: 201;
  ...Order;
}

model NoContent {
  @statusCode statusCode: 204;
}

// ---------- Операции ----------

@route("/api/health")
@get
op health(): Health;

@route("/api/users")
@post
op register(@body body: Credentials):
  | UserCreated
  | EmailTaken
  | ValidationError;

@route("/api/session")
@post
op login(@body body: Credentials): User | InvalidCredentials | ValidationError;

@route("/api/session")
@delete
op logout(): NoContent;

@route("/api/me")
@get
op me(): User | Unauthorized;

@route("/api/categories")
@get
op listCategories(): Category[];

@route("/api/promos")
@get
op listPromos(): Promo[];

@route("/api/products")
@get
op listProducts(
  @query category?: string,
  @query q?: string,
  @query priceMin?: int32,
  @query priceMax?: int32,
  @query available?: boolean,
  @query page?: int32 = 1,
  @query perPage?: int32 = 6,
): ProductPage | ValidationError;

@route("/api/products/{id}")
@get
op getProduct(@path id: string): Product | NotFound;

@route("/api/orders")
@post
op createOrder(@body body: OrderCreate):
  | OrderCreated
  | Unauthorized
  | ValidationError
  | AddressRequired
  | UnavailableItems;

@route("/api/orders")
@get
op listOrders(): Order[] | Unauthorized;

@route("/api/orders/{id}")
@get
op getOrder(@path id: string): Order | NotFound;
