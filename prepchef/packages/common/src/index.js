"use strict";
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ApiError = exports.BookingStatus = exports.Money = void 0;
var zod_1 = require("zod");
exports.Money = zod_1.z.object({ amount_cents: zod_1.z.number().int(), currency: zod_1.z.string().default('USD') });
exports.BookingStatus = zod_1.z.enum(['requested', 'awaiting_docs', 'payment_authorized', 'confirmed', 'active', 'completed', 'canceled', 'no_show', 'disputed']);
var ApiError = function (code, message, hint) { return (__assign({ code: code, message: message }, (hint ? { hint: hint } : {}))); };
exports.ApiError = ApiError;
