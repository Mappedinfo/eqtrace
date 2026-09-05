; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(assert
 (<= (- 1.0) x))
(assert
 (>= 1.0 x))
(assert
 (let ((?x81 (- (+ x 10000000000000000.0) 10000000000000000.0)))
(and (distinct x ?x81) true)))
(check-sat)
