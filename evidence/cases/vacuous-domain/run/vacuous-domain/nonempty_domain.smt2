; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(assert
 (<= 0.0 x))
(assert
 (>= 0.0 x))
(assert
 (and (distinct x 0.0) true))
(check-sat)
