; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(assert
 (<= (- 2.0) x))
(assert
 (>= 2.0 x))
(assert
 (let ((?x31 (+ (+ (* x x) (* 2.0 x)) 1.0)))
(let ((?x18 (^ (+ x 1.0) 2.0)))
(and (distinct ?x18 ?x31) true))))
(check-sat)
